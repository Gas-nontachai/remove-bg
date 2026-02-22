from __future__ import annotations

from abc import ABC, abstractmethod


class BackgroundRemover(ABC):
    @abstractmethod
    def remove(self, image_bytes: bytes) -> bytes:
        """Return processed PNG bytes with background removed."""
