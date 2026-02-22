from __future__ import annotations

import io
import zipfile
from pathlib import Path

from rq import get_current_job

from app.application.remove_background_use_case import (
    RemoveBackgroundOptions,
    RemoveBackgroundUseCase,
)
from app.infrastructure.object_storage import S3ObjectStorage
from app.infrastructure.rembg_background_remover import RembgBackgroundRemover

use_case = RemoveBackgroundUseCase(RembgBackgroundRemover())
storage = S3ObjectStorage()
storage.ensure_bucket()


def _safe_stem(name: str, fallback: str) -> str:
    stem = Path(name).stem
    safe = "".join(ch for ch in stem if ch.isalnum() or ch in ("-", "_"))
    return safe or fallback


def process_single_image_job(
    image_bytes: bytes,
    original_name: str,
    feather_radius: float,
    alpha_boost: float,
) -> dict[str, str]:
    job = get_current_job()
    job_id = job.id if job else "sync"

    options = RemoveBackgroundOptions(feather_radius=feather_radius, alpha_boost=alpha_boost)
    output_png = use_case.execute(image_bytes, options)

    key = f"jobs/{job_id}/{_safe_stem(original_name, 'result')}.png"
    storage.put_bytes(key, output_png, "image/png")

    return {
      "kind": "single",
      "key": key,
      "filename": Path(key).name,
      "content_type": "image/png",
    }


def process_batch_images_job(
    files_payload: list[dict[str, bytes | str]],
    feather_radius: float,
    alpha_boost: float,
) -> dict[str, str]:
    job = get_current_job()
    job_id = job.id if job else "sync"

    options = RemoveBackgroundOptions(feather_radius=feather_radius, alpha_boost=alpha_boost)
    output_buffer = io.BytesIO()

    with zipfile.ZipFile(output_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, payload in enumerate(files_payload, start=1):
            name = str(payload.get("name") or f"image-{index}.png")
            image_bytes = payload["bytes"]
            if not isinstance(image_bytes, bytes):
                raise ValueError(f"Invalid payload bytes for {name}")

            output_png = use_case.execute(image_bytes, options)
            safe_name = f"{_safe_stem(name, f'image-{index}')}.png"
            archive.writestr(safe_name, output_png)

    key = f"jobs/{job_id}/removed-backgrounds.zip"
    storage.put_bytes(key, output_buffer.getvalue(), "application/zip")

    return {
      "kind": "batch",
      "key": key,
      "filename": "removed-backgrounds.zip",
      "content_type": "application/zip",
    }
