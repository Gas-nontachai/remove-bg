from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from rq import Retry
from rq.job import Job
from rq.registry import FailedJobRegistry, StartedJobRegistry
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.infrastructure.image_validation import ImageValidationError, validate_image_bytes
from app.infrastructure.jobs import get_queue, get_redis_connection
from app.infrastructure.metrics import metrics
from app.infrastructure.object_storage import S3ObjectStorage

logger = logging.getLogger("rmbg.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Background Remover")

queue = get_queue()
redis_connection = get_redis_connection()
storage = S3ObjectStorage()
try:
    storage.ensure_bucket()
except Exception as exc:  # noqa: BLE001
    logger.warning("storage init failed at startup: %s", exc)


@dataclass
class SlidingWindow:
    timestamps: deque[float]


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self._buckets: dict[str, SlidingWindow] = defaultdict(lambda: SlidingWindow(deque()))

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()

        request.state.request_id = request_id
        metrics.incr("http_requests_total")

        if request.url.path.startswith("/api/"):
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            bucket = self._buckets[client_ip]
            window_start = now - 60.0

            while bucket.timestamps and bucket.timestamps[0] < window_start:
                bucket.timestamps.popleft()

            if len(bucket.timestamps) >= settings.rate_limit_per_minute:
                metrics.incr("rate_limited_total")
                return Response(
                    content='{"detail":"Rate limit exceeded. Try again in a minute."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"x-request-id": request_id},
                )

            bucket.timestamps.append(now)

        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        response.headers["x-request-id"] = request_id
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status": response.status_code,
                    "elapsed_ms": elapsed_ms,
                }
            )
        )
        return response


app.add_middleware(RequestContextMiddleware)


def _validate_options(feather_radius: float, alpha_boost: float) -> tuple[float, float]:
    if feather_radius < 0 or feather_radius > 8:
        raise HTTPException(status_code=400, detail="feather_radius must be between 0 and 8")
    if alpha_boost < 0.4 or alpha_boost > 2.5:
        raise HTTPException(status_code=400, detail="alpha_boost must be between 0.4 and 2.5")
    return feather_radius, alpha_boost


def _ensure_image_content_type(file: UploadFile) -> None:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"{file.filename or 'file'} is not an image")


def _read_and_validate_image(file: UploadFile, image_bytes: bytes) -> None:
    _ensure_image_content_type(file)
    if len(image_bytes) > settings.max_image_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{file.filename or 'file'} is too large. Max size is {settings.max_image_bytes // (1024 * 1024)} MB",
        )
    try:
        validate_image_bytes(image_bytes, max_pixels=settings.max_image_pixels)
    except ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _enqueue_retry() -> Retry | None:
    if settings.job_retry_max <= 0:
        return None
    intervals = settings.job_retry_intervals
    if not intervals:
        return Retry(max=settings.job_retry_max)
    return Retry(max=settings.job_retry_max, interval=list(intervals))


def _status_payload(job: Job) -> dict:
    status = job.get_status(refresh=True)
    meta = job.meta or {}

    payload: dict[str, str | int | None] = {
        "job_id": job.id,
        "status": status,
        "download_path": None,
        "filename": None,
        "progress": int(meta.get("progress", 0)),
        "stage": str(meta.get("stage", "queued")),
        "error": None,
        "eta_seconds": None,
    }

    if status == "failed":
        payload["error"] = str(meta.get("error") or "Job failed")

    if status == "finished":
        result = job.result or {}
        filename = result.get("filename") if isinstance(result, dict) else None
        payload["filename"] = filename
        payload["download_path"] = f"/api/jobs/{job.id}/download"
        payload["progress"] = 100
        payload["stage"] = "done"
        payload["eta_seconds"] = 0
    elif status in {"started", "queued"}:
        started_at = float(meta.get("started_at_ts", 0) or 0)
        progress = int(payload["progress"] or 0)
        if started_at > 0 and progress > 0:
            elapsed = max(1, int(time.time() - started_at))
            estimated_total = max(elapsed, int((elapsed / progress) * 100))
            payload["eta_seconds"] = max(0, estimated_total - elapsed)

    return payload


def _enqueue_cleanup_job() -> str:
    retry = _enqueue_retry()
    job = queue.enqueue(
        "app.tasks.maintenance_jobs.cleanup_expired_outputs_job",
        settings.cleanup_older_than_seconds,
        result_ttl=settings.job_result_ttl_seconds,
        failure_ttl=settings.job_failure_ttl_seconds,
        retry=retry,
    )
    return job.id


def _queue_stats() -> tuple[int, int, int]:
    try:
        started_registry = StartedJobRegistry(name=queue.name, connection=redis_connection)
        failed_registry = FailedJobRegistry(name=queue.name, connection=redis_connection)
        return queue.count, len(started_registry.get_job_ids()), len(failed_registry.get_job_ids())
    except Exception:  # noqa: BLE001
        return 0, 0, 0


@app.post("/api/jobs/remove-bg")
async def enqueue_remove_bg(
    file: UploadFile = File(...),
    feather_radius: float = Form(0.0),
    alpha_boost: float = Form(1.0),
) -> dict[str, str]:
    feather_radius, alpha_boost = _validate_options(feather_radius, alpha_boost)
    image_bytes = await file.read()
    _read_and_validate_image(file, image_bytes)

    retry = _enqueue_retry()
    job = queue.enqueue(
        "app.tasks.background_jobs.process_single_image_job",
        image_bytes,
        file.filename or "image.png",
        feather_radius,
        alpha_boost,
        result_ttl=settings.job_result_ttl_seconds,
        failure_ttl=settings.job_failure_ttl_seconds,
        retry=retry,
    )

    metrics.incr("jobs_submitted_total")
    return {"job_id": job.id, "status": "queued"}


@app.post("/api/jobs/remove-bg-batch")
async def enqueue_remove_bg_batch(
    files: list[UploadFile] = File(...),
    feather_radius: float = Form(0.0),
    alpha_boost: float = Form(1.0),
) -> dict[str, str]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > settings.max_batch_files:
        raise HTTPException(status_code=400, detail=f"Max {settings.max_batch_files} files per batch")

    feather_radius, alpha_boost = _validate_options(feather_radius, alpha_boost)

    payload: list[dict[str, bytes | str]] = []
    for index, file in enumerate(files, start=1):
        image_bytes = await file.read()
        try:
            _read_and_validate_image(file, image_bytes)
        except HTTPException as exc:
            raise HTTPException(status_code=exc.status_code, detail=f"file-{index}: {exc.detail}") from exc
        payload.append({"name": file.filename or f"file-{index}.png", "bytes": image_bytes})

    retry = _enqueue_retry()
    job = queue.enqueue(
        "app.tasks.background_jobs.process_batch_images_job",
        payload,
        feather_radius,
        alpha_boost,
        result_ttl=settings.job_result_ttl_seconds,
        failure_ttl=settings.job_failure_ttl_seconds,
        retry=retry,
    )

    metrics.incr("jobs_submitted_total")
    return {"job_id": job.id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str) -> dict:
    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Job not found") from exc

    return _status_payload(job)


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, str]:
    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Job not found") from exc

    status = job.get_status(refresh=True)
    if status in {"finished", "failed", "stopped", "canceled"}:
        return {"job_id": job.id, "status": status}

    job.cancel()
    metrics.incr("jobs_canceled_total")
    return {"job_id": job.id, "status": "canceled"}


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str) -> dict[str, str]:
    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if job.get_status(refresh=True) != "failed":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried")

    retry = _enqueue_retry()
    try:
        requeued = queue.enqueue_call(
            func=job.func_name,
            args=job.args,
            kwargs=job.kwargs,
            result_ttl=settings.job_result_ttl_seconds,
            failure_ttl=settings.job_failure_ttl_seconds,
            retry=retry,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to requeue job") from exc

    metrics.incr("jobs_retried_total")
    return {"job_id": requeued.id, "status": "queued"}


@app.get("/api/failed-jobs")
def list_failed_jobs(limit: int = 20) -> dict:
    registry = FailedJobRegistry(name=queue.name, connection=redis_connection)
    job_ids = registry.get_job_ids()[: max(1, min(limit, 100))]
    items: list[dict] = []

    for job_id in job_ids:
        try:
            job = Job.fetch(job_id, connection=redis_connection)
            payload = _status_payload(job)
            payload["created_at"] = (
                job.created_at.replace(tzinfo=timezone.utc).isoformat() if job.created_at else None
            )
            items.append(payload)
        except Exception:  # noqa: BLE001
            continue

    return {"items": items}


@app.get("/api/jobs/{job_id}/download")
def download_job_result(job_id: str) -> Response:
    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to read result from storage") from exc

    metrics.incr("downloads_total")
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/admin/cleanup")
def run_cleanup() -> dict[str, str]:
    job_id = _enqueue_cleanup_job()
    return {"cleanup_job_id": job_id, "status": "queued"}


@app.get("/api/metrics")
def get_metrics() -> dict:
    queue_depth, queue_started, queue_failed = _queue_stats()
    snapshot = metrics.snapshot()
    metrics.set_gauge("queue_depth", queue_depth)
    metrics.set_gauge("queue_started", queue_started)
    metrics.set_gauge("queue_failed", queue_failed)
    snapshot["timestamp"] = int(datetime.now(timezone.utc).timestamp())
    return snapshot


@app.get("/api/metrics/prometheus")
def get_prometheus_metrics() -> PlainTextResponse:
    queue_depth, queue_started, queue_failed = _queue_stats()
    metrics.set_gauge("queue_depth", queue_depth)
    metrics.set_gauge("queue_started", queue_started)
    metrics.set_gauge("queue_failed", queue_failed)
    return PlainTextResponse(metrics.to_prometheus_text(), media_type="text/plain; version=0.0.4")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
