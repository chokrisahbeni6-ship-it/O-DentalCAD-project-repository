# DentalCAD R12 — Docker strict synthetic validation

## Safety and scope

This is an isolated, synthetic-only research validation stack. It uses an internal Docker network, Redis without persistence, and a temporary SQLite database under `/tmp`. Do not change `DATABASE_URL`, attach production services, or use patient-identifiable data in this campaign. Passing synthetic tests is not clinical validation or clearance for patient use.

## Requirements

- Docker Engine with the Docker Compose v2 plugin
- Internet/package-index access on first build (Python and Redis images plus pinned Python dependencies)
- Enough disk space to build the Python image with SimpleITK/VTK dependencies

## Run

From the project root, run:

```bash
bash research/validation/build_and_run_strict.sh
```

The script validates Compose configuration, builds the validation image without cache, starts the isolated Redis service, runs the campaign, and requires both exit code 0 and `R12_STRICT_CAMPAIGN_PASS` in `research/validation/run_logs/CAMPAIGN_STATUS.txt`.

## Manual equivalent

```bash
docker compose -f docker-compose.validation.yml config --quiet
docker compose -f docker-compose.validation.yml build --no-cache r12-campaign
docker compose -f docker-compose.validation.yml up --abort-on-container-exit --exit-code-from r12-campaign
```

## Diagnose

- `ModuleNotFoundError: bcrypt`: inspect build logs; `backend/requirements.txt` must keep `bcrypt==4.0.1` and the build-time import/version check must pass.
- `pip check` failure: resolve dependency conflicts; do not remove authentication dependencies to force a pass.
- Redis health failure: inspect `docker compose -f docker-compose.validation.yml logs redis-validation`.
- Campaign failure: inspect all files under `research/validation/run_logs/`, especially `CAMPAIGN_STATUS.txt`, `strict_mode_failure.txt`, and pytest logs.

## Evidence

The image has not been built in environments without Docker. Only report a full pass after the script exits 0 and the status file contains `R12_STRICT_CAMPAIGN_PASS`.
