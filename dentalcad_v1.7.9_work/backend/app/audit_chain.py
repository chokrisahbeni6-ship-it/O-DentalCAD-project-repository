"""Integrity verification for the local HMAC-authenticated audit chain."""
import hashlib
import hmac
import json


def verify_chain(path: str, secret: str) -> tuple[bool, int, str]:
    if len(secret) < 64:
        return False, 0, "HMAC secret absent ou trop court"
    previous = "0" * 64
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as src:
            for line_no, line in enumerate(src, 1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("previous_hash") != previous:
                    return False, count, f"Rupture de chaîne à la ligne {line_no}"
                actual_hash = item.pop("hash", None)
                actual_hmac = item.pop("hmac", None)
                canonical = json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if not actual_hash or not hmac.compare_digest(actual_hash, expected_hash):
                    return False, count, f"Hash invalide à la ligne {line_no}"
                expected_hmac = hmac.new(secret.encode("utf-8"), actual_hash.encode("ascii"), hashlib.sha256).hexdigest()
                if not actual_hmac or not hmac.compare_digest(actual_hmac, expected_hmac):
                    return False, count, f"HMAC invalide à la ligne {line_no}"
                previous = actual_hash
                count += 1
    except (OSError, ValueError, TypeError) as exc:
        return False, count, f"Lecture impossible : {type(exc).__name__}"
    return True, count, "Chaîne valide"
