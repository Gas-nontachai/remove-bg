from __future__ import annotations

import io

from PIL import Image
import pytest

from app.infrastructure.image_validation import ImageValidationError, validate_image_bytes


def _png_bytes(width: int = 32, height: int = 32) -> bytes:
    img = Image.new('RGBA', (width, height), (255, 0, 0, 255))
    out = io.BytesIO()
    img.save(out, format='PNG')
    return out.getvalue()


def test_validate_image_bytes_ok() -> None:
    width, height, fmt = validate_image_bytes(_png_bytes(), max_pixels=10_000)
    assert width == 32
    assert height == 32
    assert fmt == 'PNG'


def test_validate_image_bytes_rejects_invalid() -> None:
    with pytest.raises(ImageValidationError):
        validate_image_bytes(b'not-an-image', max_pixels=10_000)


def test_validate_image_bytes_rejects_large_pixels() -> None:
    with pytest.raises(ImageValidationError):
        validate_image_bytes(_png_bytes(200, 200), max_pixels=10_000)
