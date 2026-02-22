# Background Remover Studio

Web app for AI background removal with manual editing tools.

## What is implemented now

- Queue + worker processing with Redis + RQ
- MinIO (S3-compatible) object storage for output files
- Job-based API flow: submit -> poll -> download
- Editor tools: brush erase/restore, wand, polygon, undo/redo, zoom/pan
- Edge refinement controls: feather + alpha boost
- Background composer and export
- Batch processing to ZIP

## Architecture

- `web` (FastAPI): validates uploads, enqueues jobs, exposes status/download API
- `worker` (RQ): runs remove-bg processing and uploads results to MinIO
- `redis`: queue backend
- `minio`: object storage backend

## Project Structure

```text
app/
  application/
  domain/
  infrastructure/
    jobs.py
    object_storage.py
  presentation/
  tasks/
static/
worker.py
main.py
```

## Environment

Copy `.env.example` and adjust values:

```bash
cp .env.example .env
```

Important vars:
- `REDIS_URL`
- `S3_ENDPOINT_URL`
- `S3_PUBLIC_ENDPOINT_URL`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET`
- `SIGNED_URL_TTL_SECONDS`

## Run with Docker Compose (recommended)

```bash
docker compose up --build
```

Services:
- Web: `http://127.0.0.1:8000`
- MinIO API: `http://127.0.0.1:9000`
- MinIO Console: `http://127.0.0.1:9001`

## Run locally (without Docker)

Start Redis + MinIO first, then:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

In another terminal:

```bash
source .venv/bin/activate
python worker.py
```

## API (job-based)

- `POST /api/jobs/remove-bg`
  - form-data: `file`, `feather_radius`, `alpha_boost`
  - returns: `{ job_id, status }`

- `POST /api/jobs/remove-bg-batch`
  - form-data: `files[]`, `feather_radius`, `alpha_boost`
  - returns: `{ job_id, status }`

- `GET /api/jobs/{job_id}`
  - returns job state (`queued`, `started`, `finished`, `failed`) and download path when done

- `GET /api/jobs/{job_id}/download`
  - streams file from MinIO via web API

- `GET /api/health`

## Notes

- `Auth + Quota` is intentionally not included yet.
