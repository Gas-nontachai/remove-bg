from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from rq.job import Job
from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.jobs import get_queue, get_redis_connection
from app.infrastructure.object_storage import S3ObjectStorage

app = FastAPI(title="Background Remover")

queue = get_queue()
redis_connection = get_redis_connection()
storage = S3ObjectStorage()
storage.ensure_bucket()

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_BATCH_FILES = 15
RATE_LIMIT_PER_MINUTE = 45


@dataclass(slots=True)
class SlidingWindow:
    timestamps: deque[float]


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self._buckets: dict[str, SlidingWindow] = defaultdict(lambda: SlidingWindow(deque()))

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self._buckets[client_ip]
        window_start = now - 60.0

        while bucket.timestamps and bucket.timestamps[0] < window_start:
            bucket.timestamps.popleft()

        if len(bucket.timestamps) >= RATE_LIMIT_PER_MINUTE:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again in a minute."}',
                status_code=429,
                media_type="application/json",
            )

        bucket.timestamps.append(now)
        return await call_next(request)


app.add_middleware(RateLimitMiddleware)


def _validate_options(feather_radius: float, alpha_boost: float) -> tuple[float, float]:
    if feather_radius < 0 or feather_radius > 8:
        raise HTTPException(status_code=400, detail="feather_radius must be between 0 and 8")
    if alpha_boost < 0.4 or alpha_boost > 2.5:
        raise HTTPException(status_code=400, detail="alpha_boost must be between 0.4 and 2.5")
    return feather_radius, alpha_boost


def _ensure_image_file(file: UploadFile) -> None:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"{file.filename or 'file'} is not an image")


def _status_payload(job: Job) -> dict[str, str | None]:
    status = job.get_status(refresh=True)
    payload: dict[str, str | None] = {
        "job_id": job.id,
        "status": status,
        "download_path": None,
        "filename": None,
    }

    if status == "failed":
        payload["error"] = "Job failed"

    if status == "finished":
        result = job.result or {}
        filename = result.get("filename") if isinstance(result, dict) else None
        payload["filename"] = filename
        payload["download_path"] = f"/api/jobs/{job.id}/download"

    return payload


@app.post("/api/jobs/remove-bg")
async def enqueue_remove_bg(
    file: UploadFile = File(...),
    feather_radius: float = Form(0.0),
    alpha_boost: float = Form(1.0),
) -> dict[str, str]:
    _ensure_image_file(file)
    feather_radius, alpha_boost = _validate_options(feather_radius, alpha_boost)
    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max size is 12 MB")

    job = queue.enqueue(
        "app.tasks.background_jobs.process_single_image_job",
        image_bytes,
        file.filename or "image.png",
        feather_radius,
        alpha_boost,
        result_ttl=86400,
        failure_ttl=86400,
    )

    return {"job_id": job.id, "status": "queued"}


@app.post("/api/jobs/remove-bg-batch")
async def enqueue_remove_bg_batch(
    files: list[UploadFile] = File(...),
    feather_radius: float = Form(0.0),
    alpha_boost: float = Form(1.0),
) -> dict[str, str]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"Max {MAX_BATCH_FILES} files per batch")

    feather_radius, alpha_boost = _validate_options(feather_radius, alpha_boost)

    payload: list[dict[str, bytes | str]] = []
    for index, file in enumerate(files, start=1):
        _ensure_image_file(file)
        image_bytes = await file.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{file.filename or f'file-{index}'} is larger than 12 MB",
            )
        payload.append({"name": file.filename or f"file-{index}.png", "bytes": image_bytes})

    job = queue.enqueue(
        "app.tasks.background_jobs.process_batch_images_job",
        payload,
        feather_radius,
        alpha_boost,
        result_ttl=86400,
        failure_ttl=86400,
    )

    return {"job_id": job.id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, str | None]:
    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    return _status_payload(job)


@app.get("/api/jobs/{job_id}/download")
def download_job_result(job_id: str) -> Response:
    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if job.get_status(refresh=True) != "finished":
        raise HTTPException(status_code=409, detail="Job is not finished")

    result = job.result or {}
    if not isinstance(result, dict) or "key" not in result:
        raise HTTPException(status_code=500, detail="Job result key not found")

    key = result["key"]
    filename = str(result.get("filename") or "result.bin")
    content_type = str(result.get("content_type") or "application/octet-stream")

    try:
        data = storage.get_bytes(key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to read result from storage") from exc

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
