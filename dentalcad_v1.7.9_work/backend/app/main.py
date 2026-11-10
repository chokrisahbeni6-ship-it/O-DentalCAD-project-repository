import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import re
import shutil
import tempfile
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import List

import httpx
from fastapi import (Depends, FastAPI, File, Form, HTTPException, Request,
                     UploadFile)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.auth import (check_password_strength, create_access_token,
                      get_current_user, hash_password, require_role,
                      verify_password)
from app.db import SessionLocal, get_db, init_db
from app import plan_tools, prosthetic
from app.guide_generator import generate_guide
from app.implant_library import load_library, public_view
from app.models_schemas import GuideParams, ImplantPlan
from app.registration import icp_align
from app.segmentation import segment_cbct_advanced
from app.viewer import PLANES, load_meta, prepare_volume, render_slice
from app.settings import settings
from app.json_logging import configure_json_logging
from app.audit_chain import verify_chain
import redis.asyncio as redis_async

configure_json_logging()
log = logging.getLogger("dentalcad")

VERSION = settings.version
ORTHANC = settings.orthanc_url
ORTHANC_AUTH = (settings.orthanc_user, settings.orthanc_password)
RESULTS_DIR = settings.results_dir
RETENTION_DAYS = settings.retention_days
MAX_RMS_MM = settings.max_rms_mm

MAX_DICOM_FILES = 2000
MAX_UPLOAD_BYTES = 1500 * 1024 * 1024
MAX_DICOM_FILE_BYTES = settings.max_dicom_file_bytes
MAX_STL_BYTES = 300 * 1024 * 1024
ROLES = {"admin", "practitioner", "assistant", "readonly"}
STAFF = ("admin", "practitioner", "assistant")
CLINICIAN = ("admin", "practitioner")

# Limites de plausibilité d'un implant (mm) : à ajuster avec vos systèmes réels
DIAMETER_RANGE = (2.0, 7.0)
LENGTH_RANGE = (4.0, 20.0)


# ───────────────────────── démarrage ─────────────────────────
def bootstrap_admin():
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    db = SessionLocal()
    try:
        if db.execute(text("SELECT COUNT(*) FROM users")).scalar() > 0:
            return
        if not email or not password:
            log.warning("Aucun utilisateur et ADMIN_EMAIL/ADMIN_PASSWORD absents : "
                        "créez un compte avec 'python -m app.create_admin'.")
            return
        db.execute(text("INSERT INTO users (email, hashed_password, full_name, role) "
                        "VALUES (:e, :p, 'Administrateur', 'admin')"),
                   {"e": email, "p": hash_password(password)})
        db.commit()
        log.info("Compte administrateur initial créé : %s", email)
    finally:
        db.close()


def purge_old_jobs():
    """Supprime les modèles 3D temporaires plus vieux que RETENTION_DAYS."""
    if not os.path.isdir(RESULTS_DIR):
        return
    limit = time.time() - RETENTION_DAYS * 86400
    for name in os.listdir(RESULTS_DIR):
        p = os.path.join(RESULTS_DIR, name)
        try:
            if os.path.isdir(p) and os.path.getmtime(p) < limit:
                shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Audit is mandatory: never start with a missing/weak HMAC key.
    if len(settings.audit_hmac_key) < 64:
        raise RuntimeError("AUDIT_HMAC_KEY obligatoire au démarrage (au moins 64 caractères)")
    init_db()            # si la base est inutilisable, le serveur NE démarre PAS
    bootstrap_admin()
    os.makedirs(RESULTS_DIR, exist_ok=True)
    purge_old_jobs()
    app.state.redis = redis_async.from_url(settings.redis_url, decode_responses=True)
    try:
        await app.state.redis.ping()
    except Exception:
        await app.state.redis.aclose()
        raise RuntimeError("Redis requis : démarrage refusé car le limiteur distribué est indisponible")
    yield
    await app.state.redis.aclose()


DEBUG = settings.debug_docs
app = FastAPI(title="DentalCAD — LABORATOIRE / NON CLINIQUE",
              description="Outil expérimental de recherche et développement exclusivement non clinique. Ne pas utiliser pour le diagnostic, la planification ou la conduite de soins, ni pour fabriquer un dispositif destiné à un patient. Résultats limités aux scénarios testés; aucune validation clinique ou certification revendiquée.",
              version=VERSION, lifespan=lifespan,
              docs_url="/docs" if DEBUG else None,
              redoc_url=None,
              openapi_url="/openapi.json" if DEBUG else None)

# Limiteur distribué Redis : fenêtre glissante atomique par adresse IP.
_RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then return 0 end
redis.call('ZADD', key, now, ARGV[4])
redis.call('PEXPIRE', key, window)
return 1
"""

@app.middleware("http")
async def request_controls(request: Request, call_next):
    started = time.perf_counter()
    status = 500
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    client = request.client.host if request.client else "unknown"
    try:
        allowed = await request.app.state.redis.eval(
            _RATE_LIMIT_LUA, 1, f"ratelimit:{client}", int(time.time() * 1000),
            60000, settings.max_requests_per_minute, f"{time.time_ns()}:{uuid.uuid4()}"
        )
    except Exception:
        log.exception("Redis indisponible : requête refusée par politique fail-closed")
        return Response(content='{"detail":"Rate limiter unavailable"}', status_code=503,
                        media_type="application/json", headers={"Retry-After": "30"})
    if not allowed:
        return Response(content='{"detail":"Rate limit exceeded"}', status_code=429,
                        media_type="application/json", headers={"Retry-After": "60"})
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        log.info("http_request", extra={"request_id": request_id, "method": request.method,
                 "path": request.url.path, "status_code": status,
                 "duration_ms": round((time.perf_counter() - started) * 1000, 2)})

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"],
                   expose_headers=["X-Guide-Validation", "X-Guide-Volume", "X-Guide-Plan-Version"])


# ───────────────────────── utilitaires ─────────────────────────
_AUDIT_CHAIN_LOCK = __import__("threading").Lock()

def _append_hash_chained_audit(event: dict) -> None:
    """Append a tamper-evident JSONL chain; chain file must be protected by OS permissions."""
    path = settings.audit_chain_file
    if len(settings.audit_hmac_key) < 64:
        raise RuntimeError("AUDIT_HMAC_KEY doit contenir au moins 64 caractères")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with _AUDIT_CHAIN_LOCK:
        previous = "0" * 64
        if os.path.exists(path):
            ok, count, message = verify_chain(path, settings.audit_hmac_key)
            if not ok:
                raise RuntimeError(f"Audit chain integrity failure; refusing to append: {message}")
            if count:
                with open(path, "rb") as src:
                    for line in src:
                        if line.strip():
                            previous = json.loads(line).get("hash", previous)
        payload = {"previous_hash": previous, **event}
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        payload["hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        payload["hmac"] = hmac.new(settings.audit_hmac_key.encode("utf-8"),
                                   payload["hash"].encode("ascii"), hashlib.sha256).hexdigest()
        with open(path, "a", encoding="utf-8") as out:
            out.write(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")

def audit(db: Session, user, action: str, target: str = "", details: str = "",
          request: Request = None):
    try:
        db.execute(text("INSERT INTO audit_log (user_id, action, target, details, ip) "
                        "VALUES (:u, :a, :t, :d, :i)"),
                   {"u": str(user["id"]) if user else None, "a": action,
                    "t": target[:256], "d": details[:2000],
                    "i": request.client.host if request and request.client else None})
        db.commit()
        _append_hash_chained_audit({"timestamp": time.time(), "user_id": str(user["id"]) if user else None,
                                    "action": action, "target": target[:256], "details": details[:2000],
                                    "ip": request.client.host if request and request.client else None})
    except Exception:
        db.rollback()
        log.exception("Échec d'écriture du journal d'audit")


_FAILS = defaultdict(deque)


def _check_rate_limit(key: str):
    now = time.time()
    q = _FAILS[key]
    while q and now - q[0] > 900:
        q.popleft()
    if len(q) >= 5:
        raise HTTPException(429, "Trop de tentatives. Réessayez dans 15 minutes.")


def get_case(db: Session, case_id: str, user) -> dict:
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(404, "Cas introuvable")
    row = db.execute(text("SELECT id, created_by FROM cases WHERE id = :i"),
                     {"i": case_id}).mappings().first()
    # Même réponse "introuvable" si le cas existe mais appartient à un autre
    if not row or (user["role"] != "admin" and str(row["created_by"]) != str(user["id"])):
        raise HTTPException(404, "Cas introuvable")
    return dict(row)


def validate_plan(raw: str) -> list:
    try:
        data = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Plan illisible (JSON invalide)")
    try:
        return plan_tools.normalize_plan(data, load_library(), DIAMETER_RANGE, LENGTH_RANGE)
    except ValueError as e:
        raise HTTPException(400, str(e))


def plan_hash(plan: list) -> str:
    return plan_tools.plan_hash(plan)


def is_dicom(content: bytes) -> bool:
    return len(content) > 132 and content[128:132] == b"DICM"


async def _stream_upload_to_path(f: UploadFile, path: str, index: int, total_before: int = 0) -> int:
    """Écrit un upload par blocs; la RAM utilisée ne dépend pas de la taille du DICOM."""
    size = 0
    header = bytearray()
    with open(path, "wb") as out:
        while True:
            chunk = await f.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_DICOM_FILE_BYTES:
                raise HTTPException(413, f"Fichier DICOM n°{index} trop volumineux (limite {MAX_DICOM_FILE_BYTES // (1024 * 1024)} Mio)")
            if total_before + size > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Volume de fichiers trop important")
            if len(header) < 132:
                header.extend(chunk[:132 - len(header)])
            out.write(chunk)
    if size <= 132 or bytes(header[128:132]) != b"DICM":
        raise HTTPException(400, f"Le fichier n°{index} n'est pas un DICOM valide")
    return size


async def _file_chunks(path: str):
    """Flux asynchrone lu depuis disque pour l'envoi à Orthanc."""
    with open(path, "rb") as src:
        while True:
            chunk = await asyncio.to_thread(src.read, 1024 * 1024)
            if not chunk:
                break
            yield chunk


async def save_dicom_uploads(files: List[UploadFile], dest: str):
    """Enregistre une série DICOM en appliquant les limites cumulées à toute la requête."""
    if not files or len(files) > MAX_DICOM_FILES:
        raise HTTPException(400, f"Entre 1 et {MAX_DICOM_FILES} fichiers DICOM attendus")
    os.makedirs(dest, exist_ok=True)
    total = 0
    try:
        for i, f in enumerate(files):
            path = os.path.join(dest, f"{i:05d}.dcm")  # nom contrôlé
            size = await _stream_upload_to_path(f, path, i + 1, total)
            total += size
            if total > MAX_UPLOAD_BYTES:  # défense en profondeur : plafond global de la série
                raise HTTPException(413, "Volume cumulé des fichiers DICOM trop important")
    except Exception:
        # Ne pas laisser de fichiers partiels/incomplets après un upload refusé.
        for name in os.listdir(dest):
            candidate = os.path.join(dest, name)
            if os.path.isfile(candidate):
                try: os.remove(candidate)
                except OSError: log.exception("Impossible de nettoyer un upload DICOM partiel")
        raise


async def save_stl(f: UploadFile, path: str):
    size = 0
    with open(path, "wb") as out:
        while chunk := await f.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_STL_BYTES:
                raise HTTPException(413, "Fichier STL trop volumineux")
            out.write(chunk)
    if size == 0:
        raise HTTPException(400, "Fichier STL vide")


def new_job_dir(user) -> tuple:
    job_id = uuid.uuid4().hex
    path = os.path.join(RESULTS_DIR, job_id)
    os.makedirs(path)
    with open(os.path.join(path, ".owner"), "w") as f:
        f.write(str(user["id"]))
    return job_id, path


# ───────────────────────── authentification ─────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}


@app.post("/api/auth/register")
def register(request: Request, email: str = Form(...), password: str = Form(...),
             full_name: str = Form(...), role: str = Form("assistant"),
             db: Session = Depends(get_db), admin=Depends(require_role("admin"))):
    """Réservé à l'administrateur."""
    email = email.strip().lower()
    if role not in ROLES:
        raise HTTPException(400, "Rôle inconnu")
    try:
        hashed = hash_password(password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        row = db.execute(text("INSERT INTO users (email, hashed_password, full_name, role) "
                              "VALUES (:e, :p, :n, :r) RETURNING id, email, role"),
                         {"e": email, "p": hashed, "n": full_name.strip()[:256], "r": role}
                         ).mappings().first()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Email déjà utilisé")
    audit(db, admin, "user_create", email, f"role={role}", request)
    return dict(row)


@app.post("/api/auth/token")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    key = f"{request.client.host if request.client else '?'}|{form.username.lower()}"
    _check_rate_limit(key)
    row = db.execute(text("SELECT * FROM users WHERE email = :e"),
                     {"e": form.username.strip().lower()}).mappings().first()
    if not row or not row["is_active"] or not verify_password(form.password, row["hashed_password"]):
        _FAILS[key].append(time.time())
        audit(db, None, "login_failed", form.username[:100], "", request)
        raise HTTPException(401, "Identifiants incorrects")
    _FAILS.pop(key, None)
    audit(db, dict(row), "login_ok", row["email"], "", request)
    return {"access_token": create_access_token(str(row["id"]), row["role"]),
            "token_type": "bearer", "role": row["role"], "full_name": row["full_name"]}


# ───────────────────────── patients, cas, plans ─────────────────────────
@app.post("/api/patients")
def create_patient(request: Request, external_id: str = Form(...), first_name: str = Form(...),
                   last_name: str = Form(...), db: Session = Depends(get_db),
                   user=Depends(require_role(*STAFF))):
    try:
        row = db.execute(text("INSERT INTO patients (external_id, first_name, last_name, created_by) "
                              "VALUES (:e, :f, :l, :u) RETURNING id, external_id"),
                         {"e": external_id[:64], "f": first_name[:128], "l": last_name[:128],
                          "u": str(user["id"])}).mappings().first()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Identifiant patient déjà existant")
    audit(db, user, "patient_create", str(row["id"]), "", request)
    return dict(row)


@app.post("/api/cases")
def create_case(request: Request, patient_id: str = Form(...), case_number: str = Form(...),
                title: str = Form(""), db: Session = Depends(get_db),
                user=Depends(require_role(*STAFF))):
    try:
        uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(404, "Patient introuvable")
    pat = db.execute(text("SELECT created_by FROM patients WHERE id = :i"),
                     {"i": patient_id}).mappings().first()
    if not pat or (user["role"] != "admin" and str(pat["created_by"]) != str(user["id"])):
        raise HTTPException(404, "Patient introuvable")
    try:
        row = db.execute(text("INSERT INTO cases (patient_id, case_number, title, created_by) "
                              "VALUES (:p, :c, :t, :u) RETURNING id, case_number, status"),
                         {"p": patient_id, "c": case_number[:64], "t": title[:256],
                          "u": str(user["id"])}).mappings().first()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Numéro de cas déjà existant")
    audit(db, user, "case_create", str(row["id"]), "", request)
    return dict(row)


@app.post("/api/cases/{case_id}/plan")
def save_plan(case_id: str, request: Request, implants: str = Form(...),
              db: Session = Depends(get_db), user=Depends(require_role(*CLINICIAN))):
    """Crée une NOUVELLE version du plan (les anciennes sont conservées)."""
    get_case(db, case_id, user)
    plan = validate_plan(implants)
    version = db.execute(text("SELECT COALESCE(MAX(version), 0) + 1 FROM plan_versions "
                              "WHERE case_id = :c"), {"c": case_id}).scalar()
    try:
        db.execute(text("INSERT INTO plan_versions (case_id, version, plan_sha256, canonical_plan, created_by) "
                        "VALUES (:c, :v, :h, CAST(:p AS jsonb), :u)"),
                   {"c": case_id, "v": version, "h": plan_hash(plan), "p": json.dumps(plan, separators=(",", ":"), sort_keys=True), "u": str(user["id"])})
        for imp in plan:
            db.execute(text("""INSERT INTO implants (case_id, system_id, diameter_mm, length_mm,
                                 position_x, position_y, position_z, axis_x, axis_y, axis_z,
                                 tooth_json, plan_version)
                               VALUES (:c, :s, :d, :l, :x, :y, :z, :ax, :ay, :az,
                                       CAST(:tooth AS jsonb), :v)"""),
                       {"c": case_id, "s": imp["system_id"], "d": imp["diameter"],
                        "l": imp["length"], "x": imp["position"][0], "y": imp["position"][1],
                        "z": imp["position"][2], "ax": imp["axis"][0], "ay": imp["axis"][1],
                        "az": imp["axis"][2], "tooth": json.dumps(imp.get("tooth")) if imp.get("tooth") else None,
                        "v": version})
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Enregistrement du plan impossible")
        raise HTTPException(500, "Enregistrement du plan impossible")
    audit(db, user, "plan_save", case_id, f"version={version} sha={plan_hash(plan)}", request)
    report = prosthetic.plan_report(plan)
    return {"status": "ok", "count": len(plan), "version": version, "validated": False,
            "report": report}


@app.get("/api/cases/{case_id}/plan")
def get_plan(case_id: str, version: int = None, db: Session = Depends(get_db),
             user=Depends(require_role(*STAFF))):
    get_case(db, case_id, user)
    if version is None:
        version = db.execute(text("SELECT MAX(version) FROM plan_versions WHERE case_id = :c"),
                             {"c": case_id}).scalar()
    if version is None:
        raise HTTPException(404, "Aucun plan pour ce cas")
    pv = db.execute(text("SELECT version, created_at, validated_at, validated_by, canonical_plan, plan_sha256 FROM plan_versions "
                         "WHERE case_id = :c AND version = :v"),
                    {"c": case_id, "v": version}).mappings().first()
    if not pv:
        raise HTTPException(404, "Version introuvable")
    rows = db.execute(text("""SELECT system_id, diameter_mm, length_mm, position_x, position_y,
                              position_z, axis_x, axis_y, axis_z, tooth_json FROM implants WHERE case_id = :c AND plan_version = :v
                              ORDER BY created_at"""), {"c": case_id, "v": version}).mappings().all()
    canonical = pv["canonical_plan"]
    if canonical is not None:
        implants = canonical if isinstance(canonical, list) else json.loads(canonical)
    else:  # Compatibilité des anciennes versions sans snapshot canonique
        implants = []
        for r in rows:
            item = {"system_id": r["system_id"], "diameter": float(r["diameter_mm"]),
                    "length": float(r["length_mm"]),
                    "position": [float(r["position_x"]), float(r["position_y"]), float(r["position_z"])]}
            if r.get("axis_x") is not None:
                item["axis"] = [float(r["axis_x"]), float(r["axis_y"]), float(r["axis_z"])]
            if r.get("tooth_json"):
                item["tooth"] = r["tooth_json"]
            implants.append(item)
    return {"version": pv["version"], "validated": pv["validated_at"] is not None,
            "validated_at": pv["validated_at"], "plan_sha256": pv["plan_sha256"],
            "implants": implants}


@app.post("/api/cases/{case_id}/plan/{version}/validate")
def validate_plan_version(case_id: str, version: int, request: Request,
                          db: Session = Depends(get_db), user=Depends(require_role(*CLINICIAN))):
    """Signature du plan par le praticien, après contrôle visuel."""
    get_case(db, case_id, user)
    res = db.execute(text("UPDATE plan_versions SET validated_by = :u, validated_at = NOW() "
                          "WHERE case_id = :c AND version = :v AND validated_at IS NULL"),
                     {"u": str(user["id"]), "c": case_id, "v": version})
    db.commit()
    if res.rowcount == 0:
        raise HTTPException(409, "Version introuvable ou déjà validée")
    audit(db, user, "plan_validate", case_id, f"version={version}", request)
    return {"status": "validated", "version": version}


@app.post("/api/cases/{case_id}/dicom")
async def upload_dicom(case_id: str, request: Request, files: List[UploadFile] = File(...),
                       db: Session = Depends(get_db), user=Depends(require_role(*STAFF))):
    get_case(db, case_id, user)
    if not files or len(files) > MAX_DICOM_FILES:
        raise HTTPException(400, f"Entre 1 et {MAX_DICOM_FILES} fichiers attendus")
    results, total = [], 0
    with tempfile.TemporaryDirectory(prefix="orthanc_upload_") as upload_dir:
        async with httpx.AsyncClient(auth=ORTHANC_AUTH, timeout=120.0) as client:
            for i, f in enumerate(files):
                name = os.path.basename(f.filename or f"fichier_{i + 1}")
                path = os.path.join(upload_dir, f"{i:05d}.dcm")
                try:
                    size = await _stream_upload_to_path(f, path, i + 1, total)
                except HTTPException as exc:
                    if exc.status_code == 400:
                        # Même un fichier rejeté compte dans le quota global de la requête.
                        size = os.path.getsize(path) if os.path.exists(path) else 0
                        total += size
                        try:
                            os.remove(path)
                        except OSError:
                            pass
                        results.append({"file": name, "ok": False, "error": "Pas un DICOM valide"})
                        continue
                    raise
                total += size
                try:
                    r = await client.post(f"{ORTHANC}/instances", content=_file_chunks(path),
                                          headers={"Content-Type": "application/dicom"})
                    results.append({"file": name, "ok": r.status_code == 200})
                except Exception:
                    log.exception("Envoi Orthanc")
                    results.append({"file": name, "ok": False, "error": "Orthanc injoignable"})
    audit(db, user, "dicom_upload", case_id, f"{len(files)} fichiers", request)
    return {"case_id": case_id, "uploads": results}


# ───────────────────────── calculs d'imagerie ─────────────────────────
@app.post("/api/segment")
async def segment(request: Request, files: List[UploadFile] = File(...),
                  threshold: int = Form(300), split_z: str = Form(""),
                  db: Session = Depends(get_db),
                  user=Depends(require_role(*STAFF))):
    if not 100 <= threshold <= 3000:
        raise HTTPException(400, "Seuil hors limites (100-3000)")
    split = None
    if split_z.strip():
        try:
            split = int(split_z)
        except ValueError:
            raise HTTPException(400, "Coupe de séparation : entier attendu")
    workdir = tempfile.mkdtemp(prefix="seg_")
    job_id = job_dir = None
    try:
        dicom_dir = os.path.join(workdir, "dcm")
        os.makedirs(dicom_dir)
        await save_dicom_uploads(files, dicom_dir)
        job_id, job_dir = new_job_dir(user)
        result = await run_in_threadpool(segment_cbct_advanced, dicom_dir, job_dir, threshold, split)
    except HTTPException:
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except ValueError as e:                      # message clair (ex. coupe hors limites)
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(422, str(e))
    except Exception:
        log.exception("Erreur de segmentation")
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(500, "Erreur de segmentation (détails dans les journaux du serveur)")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    for r in result["results"]:
        r["url"] = f"/api/files/{job_id}/{r['file']}"
    audit(db, user, "segment", job_id, f"threshold={threshold} split_z={split}", request)
    return result


@app.post("/api/register")
async def register_icp(request: Request, cbct_files: List[UploadFile] = File(...),
                       stl_file: UploadFile = File(...), threshold: int = Form(300),
                       db: Session = Depends(get_db), user=Depends(require_role(*CLINICIAN))):
    if not 100 <= threshold <= 3000:
        raise HTTPException(400, "Seuil hors limites (100-3000)")
    workdir = tempfile.mkdtemp(prefix="reg_")
    try:
        dicom_dir = os.path.join(workdir, "dcm")
        os.makedirs(dicom_dir)
        await save_dicom_uploads(cbct_files, dicom_dir)
        stl_path = os.path.join(workdir, "scan.stl")
        await save_stl(stl_file, stl_path)
        res = await run_in_threadpool(icp_align, dicom_dir, stl_path, threshold, MAX_RMS_MM)
    except HTTPException:
        raise
    except Exception:
        log.exception("Erreur de calage")
        raise HTTPException(500, "Erreur de calage (détails dans les journaux du serveur)")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    audit(db, user, "register", "", f"rms={res['rms_trimmed_mm']:.3f} ok={res['acceptable']}", request)
    out = {k: v for k, v in res.items() if k != "matrix"}
    out["rms_mm"] = res["rms_trimmed_mm"]          # nom conservé pour l'interface existante
    out["max_allowed_rms_mm"] = MAX_RMS_MM
    out["requires_visual_check"] = True
    if res["acceptable"]:
        out["status"] = "ok"
        out["transform_matrix"] = res["matrix"]
    else:
        out["status"] = "rejected"                 # aucune matrice fournie
    return out


@app.post("/api/guide/generate")
async def generate_guide_endpoint(request: Request, case_id: str = Form(...),
                                  plan_version: int = Form(...),
                                  gum_stl: UploadFile = File(...),
                                  guide_params: str = Form("{}"),
                                  db: Session = Depends(get_db),
                                  user=Depends(require_role(*CLINICIAN))):
    get_case(db, case_id, user)
    pv = db.execute(text("SELECT plan_sha256, validated_at, canonical_plan FROM plan_versions "
                         "WHERE case_id = :c AND version = :v"),
                    {"c": case_id, "v": plan_version}).mappings().first()
    if not pv:
        raise HTTPException(404, "Version de plan introuvable")
    if pv["validated_at"] is None:
        raise HTTPException(409, "Ce plan n'a pas été validé par le praticien")
    if pv["canonical_plan"] is None:
        raise HTTPException(409, "Cette version historique n'a pas de plan canonique stocké; enregistrez et validez une nouvelle version")
    submitted = pv["canonical_plan"] if isinstance(pv["canonical_plan"], list) else json.loads(pv["canonical_plan"])
    if plan_hash(submitted) != pv["plan_sha256"]:
        raise HTTPException(500, "Intégrité du plan stocké invalide : hash différent du plan canonique")
    try:
        implants = [ImplantPlan(**p) for p in submitted]
        params = GuideParams(**json.loads(guide_params))
    except Exception as e:
        raise HTTPException(400, f"Données invalides : {e}")
    workdir = tempfile.mkdtemp(prefix="guide_")
    try:
        gum_path = os.path.join(workdir, "gum.stl")
        await save_stl(gum_stl, gum_path)
        out_path = os.path.join(workdir, "guide.stl")
        result = await run_in_threadpool(generate_guide, gum_path, implants, params, out_path)
        # Controle sur toute la longueur des implants (la plaque ne voit que l'etage des trous)
        report = prosthetic.plan_report(submitted)
        if report["blocking"]:
            raise ValueError("Plan irrealisable : " + " ; ".join(report["blocking"]))
        result["validation"]["plan_warnings"] = report["warnings"][:5]
        with open(out_path, "rb") as f:
            stl_sha = hashlib.sha256(f.read()).hexdigest()
    except HTTPException:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    except ValueError as e:                      # refus motivé (ex. implants trop proches)
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(422, f"Guide refusé : {e}")
    except Exception:
        log.exception("Erreur de génération du guide")
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(500, "Erreur de génération (détails dans les journaux du serveur)")
    lib = load_library()
    unverified = sorted({p["system_id"] for p in submitted if not lib[p["system_id"]]["verified"]})
    result["validation"]["library_verified"] = not unverified
    if unverified:
        result["validation"]["library_warning"] = ("Dimensions NON verifiees (aucune source fabricant) : "
                                                   + ", ".join(unverified))
    audit(db, user, "guide_generate", case_id,
          f"plan_version={plan_version} plan_sha={pv['plan_sha256']} stl_sha={stl_sha}", request)
    return FileResponse(out_path, media_type="application/octet-stream",
                        filename="guide_chirurgical.stl",
                        headers={"X-Guide-Validation": json.dumps(result["validation"]),
                                 "X-Guide-Volume": str(result["volume_mm3"]),
                                 "X-Guide-Plan-Version": str(plan_version)},
                        background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True))


# ───────────────────────── fichiers (authentifiés) ─────────────────────────
_JOB_RE = re.compile(r"^[0-9a-f]{32}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}\.stl$")


@app.get("/api/files/{job_id}/{name}")
def get_file(job_id: str, name: str, user=Depends(get_current_user)):
    if not _JOB_RE.match(job_id) or not _NAME_RE.match(name):
        raise HTTPException(404)
    job_dir = os.path.join(RESULTS_DIR, job_id)
    try:
        with open(os.path.join(job_dir, ".owner")) as f:
            owner = f.read().strip()
    except OSError:
        raise HTTPException(404)
    if owner != str(user["id"]) and user["role"] != "admin":
        raise HTTPException(404)
    path = os.path.join(job_dir, name)
    if not os.path.isfile(path):
        raise HTTPException(404)
    return FileResponse(path, media_type="model/stl")


# ───────────────────────── visualiseur de coupes ─────────────────────────
def _owned_job_dir(job_id: str, user) -> str:
    if not _JOB_RE.match(job_id):
        raise HTTPException(404)
    job_dir = os.path.join(RESULTS_DIR, job_id)
    try:
        with open(os.path.join(job_dir, ".owner")) as f:
            owner = f.read().strip()
    except OSError:
        raise HTTPException(404)
    if owner != str(user["id"]) and user["role"] != "admin":
        raise HTTPException(404)
    return job_dir


@app.post("/api/viewer/prepare")
async def viewer_prepare(request: Request, files: List[UploadFile] = File(...),
                         db: Session = Depends(get_db),
                         user=Depends(require_role(*STAFF))):
    workdir = tempfile.mkdtemp(prefix="view_")
    job_id = job_dir = None
    try:
        dicom_dir = os.path.join(workdir, "dcm")
        os.makedirs(dicom_dir)
        await save_dicom_uploads(files, dicom_dir)
        job_id, job_dir = new_job_dir(user)
        meta = await run_in_threadpool(prepare_volume, dicom_dir, job_dir)
    except HTTPException:
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception:
        log.exception("Erreur de préparation du visualiseur")
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(500, "Impossible de lire l'examen (détails dans les journaux du serveur)")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    audit(db, user, "viewer_prepare", job_id, "", request)
    return {"job_id": job_id, **meta}


@app.get("/api/viewer/{job_id}/slice")
def viewer_slice(job_id: str, plane: str = "axial", index: int = 0,
                 low: int = 300, high: int = 500, user=Depends(get_current_user)):
    import numpy as np
    job_dir = _owned_job_dir(job_id, user)
    if plane not in PLANES:
        raise HTTPException(400, "Plan inconnu (axial, coronal ou sagittal)")
    if not (-1100 <= low <= 4000 and -1100 <= high <= 4000):
        raise HTTPException(400, "Seuils hors limites")
    try:
        meta = load_meta(job_dir)
        vol = np.load(os.path.join(job_dir, "volume.npy"), mmap_mode="r")
    except OSError:
        raise HTTPException(404, "Examen introuvable (effacé ou expiré)")
    png = render_slice(vol, meta["spacing_xyz_mm"], plane, index, low, high)
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.delete("/api/viewer/{job_id}")
def viewer_delete(job_id: str, request: Request, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    job_dir = _owned_job_dir(job_id, user)
    shutil.rmtree(job_dir, ignore_errors=True)
    audit(db, user, "viewer_delete", job_id, "", request)
    return {"status": "deleted"}


@app.get("/api/implants")
def list_implants(user=Depends(get_current_user)):
    try:
        return {"systems": public_view(load_library())}
    except ValueError as e:
        raise HTTPException(500, str(e))
