#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p research/validation/run_logs
status=0
STATUS_FILE="research/validation/run_logs/CAMPAIGN_STATUS.txt"
printf 'R12_STRICT_CAMPAIGN_RUNNING\n' > "$STATUS_FILE"
python research/validation/benchmark_registration.py > research/validation/run_logs/registration.json || status=1
python research/validation/benchmark_registration_matrix.py > research/validation/run_logs/registration_matrix.json || status=1
python research/validation/benchmark_oblique_pipeline_fallback.py > research/validation/run_logs/oblique_fallback.json || status=1
python research/validation/benchmark_mesh.py > research/validation/run_logs/mesh_fallback.json || status=1
python -m pytest -q backend/tests/test_upload_helpers_source_isolated.py backend/tests/test_oblique_dicom_roundtrip.py backend/tests/test_full_synthetic_dicom_to_registration.py > research/validation/run_logs/pytest_synthetic.txt 2>&1 || status=1
if python -c 'import SimpleITK, pydicom, bcrypt, jose, redis' >/dev/null 2>&1; then
  python research/validation/benchmark_mesh_production.py > research/validation/run_logs/mesh_production.json || status=1
  python -m pytest -q backend/tests/test_api_upload_integration.py backend/tests/test_oblique_dicom_roundtrip.py backend/tests/test_full_synthetic_dicom_to_registration.py > research/validation/run_logs/pytest_production.txt 2>&1 || status=1
  if grep -Eiq '(^|[ ,])[0-9]+ skipped|SKIPPED|ModuleNotFoundError|ImportError' research/validation/run_logs/pytest_production.txt; then
    echo 'ERROR: production pytest log contains skipped tests or import errors' | tee research/validation/run_logs/strict_mode_failure.txt
    status=1
  fi
else
  echo 'SKIPPED: production dependencies missing (requires SimpleITK, pydicom, bcrypt, python-jose, redis)' > research/validation/run_logs/production_dependencies.txt
  if [[ "${REQUIRE_PRODUCTION_TESTS:-1}" == "1" ]]; then
    echo 'ERROR: REQUIRE_PRODUCTION_TESTS=1 but production dependencies are missing.' | tee research/validation/run_logs/strict_mode_failure.txt
    status=1
  fi
fi
if [[ "$status" -eq 0 ]]; then
  printf 'R12_STRICT_CAMPAIGN_PASS\n' > "$STATUS_FILE"
else
  printf 'R12_STRICT_CAMPAIGN_FAIL\n' > "$STATUS_FILE"
fi
exit "$status"
