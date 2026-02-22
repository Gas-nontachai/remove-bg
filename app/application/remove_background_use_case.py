from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageFilter

from app.domain.background_remover import BackgroundRemover


@dataclass
class RemoveBackgroundOptions:
    feather_radius: float = 0.0
    alpha_boost: float = 1.0


class RemoveBackgroundUseCase:
    def __init__(self, remover: BackgroundRemover) -> None:
        self._remover = remover

    def execute(self, image_bytes: bytes, options: RemoveBackgroundOptions | None = None) -> bytes:
        if not image_bytes:
            raise ValueError("Uploaded file is empty")

        opts = options or RemoveBackgroundOptions()
        output_png = self._remover.remove(image_bytes)
        return self._refine_alpha(output_png, opts)

    def _refine_alpha(self, png_bytes: bytes, options: RemoveBackgroundOptions) -> bytes:
        needs_refine = options.feather_radius > 0 or abs(options.alpha_boost - 1.0) > 1e-3
        if not needs_refine:
            return png_bytes

        with Image.open(io.BytesIO(png_bytes)) as image:
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")

            if options.feather_radius > 0:
                alpha = alpha.filter(ImageFilter.GaussianBlur(radius=options.feather_radius))

            if abs(options.alpha_boost - 1.0) > 1e-3:
                boost = max(0.4, min(2.5, options.alpha_boost))
                alpha = alpha.point(
                    lambda value: int(
                        max(0, min(255, ((value / 255.0 - 0.5) * boost + 0.5) * 255))
                    )
                )

            rgba.putalpha(alpha)
            output = io.BytesIO()
            rgba.save(output, format="PNG")
            return output.getvalue()
