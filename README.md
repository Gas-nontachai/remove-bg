# Background Remover Studio

Production-oriented background-removal web app with editor tools, async queue workers, and MinIO object storage.

## Current Capability (Auth excluded)

- Async job lifecycle: submit, poll, cancel, retry failed, cleanup
- Progress + stage + ETA in job status
- Worker reliability: retry/backoff + failed job registry endpoint
- Storage hardening: MinIO/S3 + prefix-based cleanup strategy
- Validation/security: MIME + Pillow image verify + size/pixel limits + rate limit + request-id
- Observability: JSON request logs + metrics JSON + Prometheus endpoint
- Monitoring stack: Prometheus + Grafana (optional compose profile)
- UI polish: compare slider, keyboard shortcuts, autosave, failed-jobs retry panel
- Tests: unit + API + task tests, plus dockerized integration smoke in CI
- Release/deploy artifacts: CI, release workflow, deploy workflow, operations runbook

## Key API Endpoints

- `POST /api/jobs/remove-bg`
- `POST /api/jobs/remove-bg-batch`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/retry`
- `GET /api/jobs/{job_id}/download`
- `GET /api/failed-jobs`
- `POST /api/admin/cleanup`
- `GET /api/metrics`
- `GET /api/metrics/prometheus`
- `GET /api/health`

## Environment Profiles

- `.env.dev` for local dev defaults
- `.env.prod.example` as production template
- `.env` active local file

Recommended:

```bash
cp .env.dev .env
```

For production, create `.env.prod` from `.env.prod.example` and replace all secrets.

## Run Locally (Python)

Prerequisite: Redis + MinIO running on localhost.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_storage.py
uvicorn main:app --reload
```

In another terminal:

```bash
source .venv/bin/activate
python worker.py
```

## Run with Docker Compose

```bash
docker compose up --build -d
```

Optional monitoring stack:

```bash
docker compose --profile monitoring up -d
```

Ports:
- App: `8000`
- MinIO: `9000` (API), `9001` (console)
- Prometheus: `9090`
- Grafana: `3000`

## Performance Tuning

Use env values:
- `WORKER_CONCURRENCY`
- `RATE_LIMIT_PER_MINUTE`
- `MAX_BATCH_FILES`
- `JOB_RETRY_MAX`, `JOB_RETRY_INTERVALS`

Quick submit benchmark:

```bash
python scripts/benchmark_jobs.py --count 20
```

## Testing

Unit/API tests:

```bash
python -m pytest -q
```

Integration smoke (requires running stack):

```bash
./tests/integration_smoke.sh
```

## CI/CD

- CI: `.github/workflows/ci.yml`
  - unit tests
  - docker-compose integration smoke
- Release tags: `.github/workflows/release.yml` (`v*.*.*`)
- Manual deploy workflow: `.github/workflows/deploy.yml`

## Operations

Backup/restore and secret rotation guide:

- `docs/operations.md`
