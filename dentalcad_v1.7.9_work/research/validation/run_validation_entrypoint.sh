#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../.."
LOG_DIR="research/validation/run_logs"
mkdir -p "$LOG_DIR"
STATUS_FILE="$LOG_DIR/CAMPAIGN_STATUS.txt"
printf 'R12_STRICT_CAMPAIGN_RUNNING\n' > "$STATUS_FILE"
if ! python -c 'import SimpleITK,pydicom,vtk,redis,bcrypt,jose'; then
  echo 'ERROR: required production dependencies failed to import' > "$LOG_DIR/strict_mode_failure.txt"
  printf 'R12_STRICT_CAMPAIGN_FAIL\n' > "$STATUS_FILE"
  exit 1
fi
if ! python -c 'import os,redis; redis.Redis.from_url(os.environ["REDIS_URL"]).ping()'; then
  echo 'ERROR: Redis validation service is unavailable' > "$LOG_DIR/strict_mode_failure.txt"
  printf 'R12_STRICT_CAMPAIGN_FAIL\n' > "$STATUS_FILE"
  exit 1
fi
exec env REQUIRE_PRODUCTION_TESTS=1 bash research/validation/run_synthetic_campaign.sh
