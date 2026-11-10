"""Execute the exact upload helper definitions from production main.py without importing unrelated auth/Redis modules.

This exercises the production helper code, not the HTTP route or full app lifespan.
"""
import ast
import io
import logging
import os
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend" / "app" / "main.py"


def load_upload_helpers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    wanted = {"_stream_upload_to_path", "save_dicom_uploads"}
    nodes = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name in wanted]
    assert {n.name for n in nodes} == wanted
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {
        "UploadFile": UploadFile, "HTTPException": HTTPException,
        "List": list, "os": os, "log": logging.getLogger("upload-test"),
        "MAX_DICOM_FILES": 2000, "MAX_UPLOAD_BYTES": 1500 * 1024 * 1024,
        "MAX_DICOM_FILE_BYTES": 256 * 1024 * 1024,
    }
    exec(compile(module, str(SOURCE), "exec"), ns)
    return ns


def dicom_bytes(payload=b"x"):
    return b"\0" * 128 + b"DICM" + payload


@pytest.mark.asyncio
async def test_production_upload_helpers_accept_valid_series(tmp_path):
    ns = load_upload_helpers()
    files = [UploadFile(filename="a.dcm", file=io.BytesIO(dicom_bytes(b"a"))),
             UploadFile(filename="b.dcm", file=io.BytesIO(dicom_bytes(b"b")))]
    await ns["save_dicom_uploads"](files, str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["00000.dcm", "00001.dcm"]
    assert (tmp_path / "00000.dcm").read_bytes() == dicom_bytes(b"a")


@pytest.mark.asyncio
async def test_production_upload_helpers_reject_invalid_dicom_and_clean_partial(tmp_path):
    ns = load_upload_helpers()
    files = [UploadFile(filename="good.dcm", file=io.BytesIO(dicom_bytes())),
             UploadFile(filename="bad.dcm", file=io.BytesIO(b"not dicom"))]
    with pytest.raises(HTTPException) as exc:
        await ns["save_dicom_uploads"](files, str(tmp_path))
    assert exc.value.status_code == 400
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_production_upload_helpers_enforce_cumulative_limit(tmp_path):
    ns = load_upload_helpers()
    ns["MAX_UPLOAD_BYTES"] = 150
    files = [UploadFile(filename="a.dcm", file=io.BytesIO(dicom_bytes(b"a" * 10))),
             UploadFile(filename="b.dcm", file=io.BytesIO(dicom_bytes(b"b" * 10)))]
    with pytest.raises(HTTPException) as exc:
        await ns["save_dicom_uploads"](files, str(tmp_path))
    assert exc.value.status_code == 413
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_production_upload_helpers_enforce_single_file_limit(tmp_path):
    ns = load_upload_helpers()
    ns["MAX_DICOM_FILE_BYTES"] = 140
    files = [UploadFile(filename="large.dcm", file=io.BytesIO(dicom_bytes(b"z" * 20)))]
    with pytest.raises(HTTPException) as exc:
        await ns["save_dicom_uploads"](files, str(tmp_path))
    assert exc.value.status_code == 413
    assert list(tmp_path.iterdir()) == []
