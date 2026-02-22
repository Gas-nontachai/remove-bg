# Background Remover Studio

Production-oriented background-removal web app with editor tools, async job queue, and MinIO storage.

## Implemented Scope

1. Job lifecycle management
- async jobs with status polling
- cancel API
- cleanup jobs (manual + scheduler)

2. Progress reporting
- per-job progress/stage metadata
- frontend progress bars for single/batch

3. Worker reliability
- retry policy with backoff
- failed jobs listing endpoint

4. Storage hardening
- MinIO/S3 object storage
- cleanup of expired outputs

5. Validation and security
- MIME + image bytes verification with Pillow
- max bytes/max pixels limit
- request rate limit
- request-id per API call

6. Testing
- pytest suite for API, task, and validation logic

7. Observability
- structured request logging
- in-app metrics endpoint

8. DX / Operations
- scripts for storage init and cleanup
- GitHub Actions CI workflow

9. UI/UX polish
- before/after compare slider
- keyboard shortcuts
- autosave editor settings

## Architecture

- `web` (FastAPI): validate input, enqueue jobs, provide status/download APIs
- `worker` (RQ): execute remove-bg tasks and cleanup tasks
- `redis`: queue backend
- `minio`: object storage

## Project Structure

```text
app/
  application/
  domain/
  infrastructure/
    image_validation.py
    jobs.py
    metrics.py
    object_storage.py
  presentation/
  tasks/
scripts/
  init_storage.py
  run_cleanup.py
static/
tests/
worker.py
main.py
```

## Environment

```bash
cp .env.example .env
```

Main variables:
- `REDIS_URL`
- `S3_ENDPOINT_URL`
- `S3_PUBLIC_ENDPOINT_URL`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET`
- `MAX_IMAGE_BYTES`
- `MAX_BATCH_FILES`
- `MAX_IMAGE_PIXELS`
- `JOB_RETRY_MAX`
- `JOB_RETRY_INTERVALS`
- `CLEANUP_ENABLED`
- `CLEANUP_INTERVAL_SECONDS`
- `CLEANUP_OLDER_THAN_SECONDS`

## Run (Docker Compose)

```bash
docker compose up --build
```

Services:
- Web: `http://127.0.0.1:8000`
- MinIO API: `http://127.0.0.1:9000`
- MinIO Console: `http://127.0.0.1:9001`

## Run (Local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_storage.py
uvicorn main:app --reload
```

Worker terminal:

```bash
source .venv/bin/activate
python worker.py
```

## API

- `POST /api/jobs/remove-bg`
- `POST /api/jobs/remove-bg-batch`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `GET /api/jobs/{job_id}/download`
- `GET /api/failed-jobs`
- `POST /api/admin/cleanup`
- `GET /api/metrics`
- `GET /api/health`

## Shortcuts

- `B` brush erase
- `E` brush restore
- `W` wand erase
- `P` polygon erase
- `Z` undo
- `Y` redo
- `Space` hold pan

## Tests

```bash
python3 -m pytest -q
```

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`
