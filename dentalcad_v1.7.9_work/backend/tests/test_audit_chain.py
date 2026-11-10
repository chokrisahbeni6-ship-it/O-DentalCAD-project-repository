import hashlib
import hmac
import json
from app.audit_chain import verify_chain


def write_event(path, secret, event):
    payload = {"previous_hash": "0" * 64, **event}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    payload["hash"] = digest
    payload["hmac"] = hmac.new(secret.encode(), digest.encode("ascii"), hashlib.sha256).hexdigest()
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def test_audit_chain_detects_tampering(tmp_path):
    secret = "a" * 64
    path = tmp_path / "audit.jsonl"
    write_event(path, secret, {"action": "login", "timestamp": 1})
    assert verify_chain(str(path), secret) == (True, 1, "Chaîne valide")
    path.write_text(path.read_text().replace('"login"', '"delete"'))
    ok, count, message = verify_chain(str(path), secret)
    assert not ok and count == 0 and "Hash invalide" in message


def test_audit_chain_rejects_wrong_hmac_key(tmp_path):
    path = tmp_path / "audit.jsonl"
    write_event(path, "a" * 64, {"action": "login", "timestamp": 1})
    assert not verify_chain(str(path), "b" * 64)[0]
