from __future__ import annotations

from app.domain.background_remover import BackgroundRemover


class RemoveBackgroundUseCase:
    def __init__(self, remover: BackgroundRemover) -> None:
        self._remover = remover

    def execute(self, image_bytes: bytes) -> bytes:
        if not image_bytes:
            raise ValueError("Uploaded file is empty")
        return self._remover.remove(image_bytes)
