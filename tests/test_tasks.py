from __future__ import annotations

import io
import sys
import types

from PIL import Image

# Stub rembg for test environment without onnx model packages.
if 'rembg' not in sys.modules:
    rembg_stub = types.SimpleNamespace(
        new_session=lambda: object(),
        remove=lambda image_bytes, session=None: image_bytes,
    )
    sys.modules['rembg'] = rembg_stub

from app.tasks import background_jobs


class StubStorage:
    def __init__(self) -> None:
        self.objects = {}

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)


def _image_bytes() -> bytes:
    image = Image.new('RGBA', (20, 20), (255, 0, 0, 255))
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def test_process_single_image_job(monkeypatch) -> None:
    storage = StubStorage()
    monkeypatch.setattr(background_jobs, 'storage', storage)

    result = background_jobs.process_single_image_job(_image_bytes(), 'sample.png', 0.0, 1.0)

    assert result['content_type'] == 'image/png'
    assert result['key'] in storage.objects
