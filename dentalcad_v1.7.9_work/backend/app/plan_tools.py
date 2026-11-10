"""Normalisation et empreinte (hash) d'un plan d'implants. Logique pure, testable."""
import hashlib
import json
import math

import numpy as np

from app.implant_library import check_implant

DEFAULT_AXIS = (0.0, 0.0, -1.0)     # vers l'apex (os), repere du scan : +Z = vers le haut
MAX_TILT_DEG = 35.0                  # inclinaison maximale acceptee par rapport a la verticale


def _norm_axis(raw, i):
    try:
        a = np.array([float(v) for v in raw], dtype=float)
    except (TypeError, ValueError):
        raise ValueError(f"Implant {i} : axe illisible")
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError(f"Implant {i} : l'axe doit contenir 3 nombres")
    n = float(np.linalg.norm(a))
    if n < 1e-9:
        raise ValueError(f"Implant {i} : axe nul")
    a /= n
    if a[2] >= 0.0:
        raise ValueError(f"Implant {i} : l'axe doit pointer vers l'apex (composante Z négative)")
    tilt = math.degrees(math.acos(min(1.0, abs(float(a[2])))))
    if tilt > MAX_TILT_DEG:
        raise ValueError(f"Implant {i} : inclinaison {tilt:.1f} deg au-dela du maximum "
                         f"({MAX_TILT_DEG:.0f} deg par rapport a la verticale)")
    return [round(float(v), 4) for v in a]


def normalize_plan(data, library, diameter_range, length_range):
    if not isinstance(data, list) or not 1 <= len(data) <= 32:
        raise ValueError("Le plan doit contenir de 1 a 32 implants")
    out = []
    for i, imp in enumerate(data, 1):
        try:
            d, l = float(imp["diameter"]), float(imp["length"])
            pos = [float(v) for v in imp["position"]]
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Implant {i} : donnees manquantes ou invalides")
        if len(pos) != 3 or not all(math.isfinite(v) for v in [d, l, *pos]):
            raise ValueError(f"Implant {i} : valeurs non valides")
        if not diameter_range[0] <= d <= diameter_range[1]:
            raise ValueError(f"Implant {i} : diametre {d} mm hors limites {diameter_range}")
        if not length_range[0] <= l <= length_range[1]:
            raise ValueError(f"Implant {i} : longueur {l} mm hors limites {length_range}")
        if any(abs(v) > 1000 for v in pos):
            raise ValueError(f"Implant {i} : position aberrante")
        system_id = str(imp.get("system_id") or "")[:64] or None
        try:
            check_implant(library, system_id, d, l)
        except ValueError as e:
            raise ValueError(f"Implant {i} : {e}")
        tooth = _norm_tooth(imp.get("tooth"), i)
        if imp.get("axis") is not None:
            axis = _norm_axis(imp["axis"], i)
        elif tooth and tooth["axis"]:
            axis = _norm_axis(tooth["axis"], i)      # planification a partir de la dent
        else:
            axis = list(DEFAULT_AXIS)
        item = {"system_id": system_id, "diameter": round(d, 2), "length": round(l, 2),
                "position": [round(v, 3) for v in pos], "axis": axis}
        if tooth:
            item["tooth"] = tooth
        out.append(item)
    return out


def _norm_tooth(raw, i):
    """Dent prevue (facultative) : {"fdi": "36", "center": [x,y,z], "axis": [x,y,z]}."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"Implant {i} : 'tooth' doit etre un objet")
    try:
        c = [float(v) for v in raw["center"]]
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Implant {i} : dent prevue sans 'center' valide")
    if len(c) != 3 or not all(math.isfinite(v) for v in c) or any(abs(v) > 1000 for v in c):
        raise ValueError(f"Implant {i} : centre de la dent non valide")
    axis = None
    if raw.get("axis") is not None:
        try:
            a = np.array([float(v) for v in raw["axis"]], dtype=float)
        except (TypeError, ValueError):
            raise ValueError(f"Implant {i} : axe de la dent illisible")
        if a.shape != (3,) or not np.all(np.isfinite(a)) or np.linalg.norm(a) < 1e-9:
            raise ValueError(f"Implant {i} : axe de la dent non valide")
        axis = [round(float(v), 4) for v in a / np.linalg.norm(a)]
    fdi = str(raw.get("fdi") or "")[:8] or None
    return {"fdi": fdi, "center": [round(v, 3) for v in c], "axis": axis}


def _is_default_axis(axis):
    return all(abs(a - b) < 1e-4 for a, b in zip(axis, DEFAULT_AXIS))


def plan_hash(plan):
    """Axe et dent prevue n'entrent dans l'empreinte que s'ils sont presents (et l'axe non
    par defaut) : les plans enregistres avant gardent exactement la meme empreinte."""
    rows = []
    for p in plan:
        row = [p.get("system_id") or "", p["diameter"], p["length"], *p["position"]]
        ax = p.get("axis")
        if ax is not None and not _is_default_axis(ax):
            row += list(ax)
        if p.get("tooth"):
            row.append("tooth:" + json.dumps(p["tooth"], sort_keys=True))
        rows.append(row)
    try:
        rows = sorted(rows)
    except TypeError:                      # lignes de types differents au meme rang (cas rare)
        rows = sorted(rows, key=json.dumps)
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()
