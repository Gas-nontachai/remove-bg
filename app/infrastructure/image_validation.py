from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError


class ImageValidationError(ValueError):
    pass


def validate_image_bytes(image_bytes: bytes, max_pixels: int) -> tuple[int, int, str]:
    if not image_bytes:
        raise ImageValidationError("Uploaded file is empty")

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
        with Image.open(io.BytesIO(image_bytes)) as image:
            width, height = image.size
            fmt = (image.format or "").upper() or "UNKNOWN"
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError("Invalid or corrupted image file") from exc

    if width <= 0 or height <= 0:
        raise ImageValidationError("Invalid image dimensions")
    if width * height > max_pixels:
        raise ImageValidationError(f"Image too large in pixels. Max allowed is {max_pixels}")

    return width, height, fmt
