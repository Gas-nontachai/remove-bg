from __future__ import annotations

import asyncio
import io
import time
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.application.remove_background_use_case import (
    RemoveBackgroundOptions,
    RemoveBackgroundUseCase,
)
from app.infrastructure.rembg_background_remover import RembgBackgroundRemover

app = FastAPI(title="Background Remover")

use_case = RemoveBackgroundUseCase(RembgBackgroundRemover())
inference_semaphore = asyncio.Semaphore(2)

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


def _build_options(feather_radius: float, alpha_boost: float) -> RemoveBackgroundOptions:
    if feather_radius < 0 or feather_radius > 8:
        raise HTTPException(status_code=400, detail="feather_radius must be between 0 and 8")
    if alpha_boost < 0.4 or alpha_boost > 2.5:
        raise HTTPException(status_code=400, detail="alpha_boost must be between 0.4 and 2.5")
    return RemoveBackgroundOptions(feather_radius=feather_radius, alpha_boost=alpha_boost)


def _ensure_image_file(file: UploadFile) -> None:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"{file.filename or 'file'} is not an image")


def _safe_output_name(file: UploadFile, index: int) -> str:
    stem = Path(file.filename or f"image-{index}").stem
    safe = "".join(ch for ch in stem if ch.isalnum() or ch in ("-", "_")) or f"image-{index}"
    return f"{safe}.png"


@app.post("/api/remove-bg")
async def remove_bg(file: UploadFile = File(...)) -> Response:
    _ensure_image_file(file)
    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max size is 12 MB")
    options = _build_options(feather_radius=0.0, alpha_boost=1.0)

    try:
        async with inference_semaphore:
            output_png = await asyncio.to_thread(use_case.execute, image_bytes, options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Background removal failed") from exc

    return Response(content=output_png, media_type="image/png")


@app.post("/api/remove-bg-refined")
async def remove_bg_refined(
    file: UploadFile = File(...),
    feather_radius: float = Form(0.0),
    alpha_boost: float = Form(1.0),
) -> Response:
    _ensure_image_file(file)
    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max size is 12 MB")
    options = _build_options(feather_radius=feather_radius, alpha_boost=alpha_boost)

    try:
        async with inference_semaphore:
            output_png = await asyncio.to_thread(use_case.execute, image_bytes, options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Background removal failed") from exc

    return Response(content=output_png, media_type="image/png")


@app.post("/api/remove-bg-batch")
async def remove_bg_batch(
    files: list[UploadFile] = File(...),
    feather_radius: float = Form(0.0),
    alpha_boost: float = Form(1.0),
) -> Response:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"Max {MAX_BATCH_FILES} files per batch")

    options = _build_options(feather_radius=feather_radius, alpha_boost=alpha_boost)
    output_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(output_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, file in enumerate(files, start=1):
                _ensure_image_file(file)
                image_bytes = await file.read()
                if len(image_bytes) > MAX_IMAGE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"{file.filename or f'file-{index}'} is larger than 12 MB",
                    )

                async with inference_semaphore:
                    output_png = await asyncio.to_thread(use_case.execute, image_bytes, options)
                archive.writestr(_safe_output_name(file, index), output_png)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Batch background removal failed") from exc

    return Response(
        content=output_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="removed-backgrounds.zip"'},
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
