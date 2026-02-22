from __future__ import annotations

from rembg import new_session, remove

from app.domain.background_remover import BackgroundRemover


class RembgBackgroundRemover(BackgroundRemover):
    def __init__(self) -> None:
        # Keep one session alive to avoid reloading model every request.
        self._session = new_session()

    def remove(self, image_bytes: bytes) -> bytes:
        return remove(image_bytes, session=self._session)
