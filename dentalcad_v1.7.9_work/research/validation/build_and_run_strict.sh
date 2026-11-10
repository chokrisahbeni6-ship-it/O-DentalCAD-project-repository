#!/usr/bin/env bash
# Build and run the isolated DentalCAD R12 strict synthetic validation stack.
# Does not target production services or patient data.
set -euo pipefail
cd "$(dirname "$0")/../.."
command -v docker >/dev/null 2>&1 || { echo 'ERROR: Docker CLI not found.' >&2; exit 127; }
docker compose version >/dev/null 2>&1 || { echo 'ERROR: Docker Compose plugin is required.' >&2; exit 127; }
mkdir -p research/validation/run_logs
# Fail closed: the Compose stack uses an internal network and synthetic SQLite DB.
docker compose -f docker-compose.validation.yml config --quiet
docker compose -f docker-compose.validation.yml build --no-cache r12-campaign
set +e
docker compose -f docker-compose.validation.yml up --abort-on-container-exit --exit-code-from r12-campaign
rc=$?
set -e
status_file='research/validation/run_logs/CAMPAIGN_STATUS.txt'
if [[ ! -f "$status_file" ]]; then
  echo 'ERROR: campaign status file was not produced.' >&2
  exit 1
fi
status="$(tr -d '\r\n' < "$status_file")"
printf 'Campaign status: %s\n' "$status"
if [[ "$rc" -ne 0 || "$status" != 'R12_STRICT_CAMPAIGN_PASS' ]]; then
  echo 'STRICT CAMPAIGN FAILED. Inspect research/validation/run_logs/.' >&2
  exit 1
fi
echo 'STRICT CAMPAIGN PASSED.'
