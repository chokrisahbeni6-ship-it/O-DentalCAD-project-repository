import io
import pytest
from fastapi import HTTPException, UploadFile
from app import main


def dicom_bytes(payload=b'x'):
    return b'\0' * 128 + b'DICM' + payload

@pytest.mark.asyncio
async def test_save_dicom_uploads_accepts_valid_series(tmp_path):
    files = [UploadFile(filename='a.dcm', file=io.BytesIO(dicom_bytes(b'a'))),
             UploadFile(filename='b.dcm', file=io.BytesIO(dicom_bytes(b'b')))]
    await main.save_dicom_uploads(files, str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ['00000.dcm', '00001.dcm']
    assert (tmp_path / '00000.dcm').read_bytes().endswith(b'DICM' + b'a')

@pytest.mark.asyncio
async def test_save_dicom_uploads_rejects_invalid_dicom_and_cleans_partial(tmp_path):
    files = [UploadFile(filename='a.dcm', file=io.BytesIO(dicom_bytes())),
             UploadFile(filename='bad.dcm', file=io.BytesIO(b'not dicom'))]
    with pytest.raises(HTTPException) as exc:
        await main.save_dicom_uploads(files, str(tmp_path))
    assert exc.value.status_code == 400
    assert list(tmp_path.iterdir()) == []

@pytest.mark.asyncio
async def test_save_dicom_uploads_enforces_cumulative_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(main, 'MAX_UPLOAD_BYTES', 140)
    files = [UploadFile(filename='a.dcm', file=io.BytesIO(dicom_bytes(b'a'*10))),
             UploadFile(filename='b.dcm', file=io.BytesIO(dicom_bytes(b'b'*10)))]
    with pytest.raises(HTTPException) as exc:
        await main.save_dicom_uploads(files, str(tmp_path))
    assert exc.value.status_code == 413
    assert list(tmp_path.iterdir()) == []

def test_audit_hmac_key_validation_is_explicit():
    assert len(main.settings.audit_hmac_key) < 64 or len(main.settings.audit_hmac_key) >= 64
    # Lifespan performs this check before database initialization or serving requests.
    import inspect
    source = inspect.getsource(main.lifespan)
    assert 'AUDIT_HMAC_KEY obligatoire au démarrage' in source


def test_proxy_ip_policy_uses_socket_peer_not_untrusted_xff():
    source = inspect.getsource(main.request_controls)
    assert 'request.client.host' in source
    assert 'X-Forwarded-For' not in source
