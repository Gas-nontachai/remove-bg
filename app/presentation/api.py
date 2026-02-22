from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.application.remove_background_use_case import RemoveBackgroundUseCase
from app.infrastructure.rembg_background_remover import RembgBackgroundRemover

app = FastAPI(title="Background Remover")

use_case = RemoveBackgroundUseCase(RembgBackgroundRemover())


@app.post("/api/remove-bg")
async def remove_bg(file: UploadFile = File(...)) -> Response:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file")

    image_bytes = await file.read()

    try:
        output_png = use_case.execute(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Background removal failed") from exc

    return Response(content=output_png, media_type="image/png")


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
