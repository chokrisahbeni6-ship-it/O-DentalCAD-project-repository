# DentalCAD R12 technical package — import audit

Audit date: 2026-11-10
Source archive: `DentalCAD_R12_Technical_Workers_20261019(1).zip`
Project directory in archive: `dentalcad_v1.7.9_work`
Scope: non-clinical laboratory/research software only.

## Package integrity and contents
- Source ZIP integrity check: passed (`unzip -t`, no compressed-data errors).
- Extracted project files: 141.
- Project source identifies itself as version 1.7.9; R12 refers to the validation campaign/tooling. Do not relabel the application itself as version 12.
- No `.env`, private-key/certificate, local database, DICOM, NIfTI, or STL files were found by filename scan.
- `.env.example` contains empty credential fields; do not commit a populated `.env`.

## Rechecked static validations in this audit environment
- `bash -n research/validation/run_synthetic_campaign.sh`: PASS.
- `python -m compileall -q backend/app backend/tests research/validation`: PASS.
- `node --check frontend/app.js`: PASS.
- YAML parse of `docker-compose.yml` and `docker-compose.validation.yml`: PASS.

## Existing R12 execution evidence — strict FAIL
`research/validation/run_logs/CAMPAIGN_STATUS.txt` says `R12_STRICT_CAMPAIGN_FAIL`.
`FINAL_VERDICT.txt` says partial local synthetic tests only and explicitly says not validated.
The execution report records 4 passed, 2 skipped, and a strict-mode exit code 1. Production dependencies (SimpleITK, pydicom, redis, bcrypt, python-jose) were missing and Docker/Podman was unavailable. DICOM roundtrip, full pipeline, real Redis, production HTTP/API integration, and production mesh export remain unverified.

## Required next validation
Run the strict Docker campaign on a machine with Docker/Compose and network access, then inspect the generated production logs. A zero exit from the non-strict partial runner is not sufficient. Do not claim clinical validation, regulatory certification, or suitability for patient care.

## Import safety
This audit did not modify application source files. The original uploaded ZIP remains unchanged. This report is additive only.
