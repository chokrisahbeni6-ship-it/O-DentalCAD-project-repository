"""Centralized environment settings for DentalCAD backend."""
import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer setting: {name}") from exc


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"Invalid numeric setting: {name}") from exc


@dataclass(frozen=True)
class Settings:
    version: str = os.getenv("DENTALCAD_VERSION", "1.7.9")
    debug_docs: bool = os.getenv("DEBUG_DOCS", "0") == "1"
    orthanc_url: str = os.getenv("ORTHANC_URL", "http://orthanc:8042")
    orthanc_user: str = os.getenv("ORTHANC_USER", "")
    orthanc_password: str = os.getenv("ORTHANC_PASSWORD", "")
    results_dir: str = os.getenv("RESULTS_DIR", "/data/results")
    retention_days: int = _int("RESULTS_RETENTION_DAYS", 7)
    max_rms_mm: float = _float("REG_MAX_RMS_MM", 0.5)
    max_dicom_file_bytes: int = _int("MAX_DICOM_FILE_BYTES", 256 * 1024 * 1024)
    max_requests_per_minute: int = _int("MAX_REQUESTS_PER_MINUTE", 120)
    audit_chain_file: str = os.getenv("AUDIT_CHAIN_FILE", "/data/results/audit-chain.jsonl")
    audit_hmac_key: str = os.getenv("AUDIT_HMAC_KEY", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    rate_limit_fail_closed: bool = os.getenv("RATE_LIMIT_FAIL_CLOSED", "1") == "1"


settings = Settings()
