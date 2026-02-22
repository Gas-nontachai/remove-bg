from __future__ import annotations

from rembg import remove

from app.domain.background_remover import BackgroundRemover


class RembgBackgroundRemover(BackgroundRemover):
    def remove(self, image_bytes: bytes) -> bytes:
        return remove(image_bytes)
