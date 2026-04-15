from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings


router = APIRouter(prefix="/api", tags=["system"])


class HealthResponse(BaseModel):
    status: str
    output_dir: str


class OpenFolderRequest(BaseModel):
    path: str | None = None


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", output_dir=str(settings.resolved_output_dir()))


@router.post("/open-folder")
def open_folder(
    req: OpenFolderRequest,
    settings: Settings = Depends(get_settings),
) -> dict:
    target = Path(req.path) if req.path else settings.resolved_output_dir()
    target.mkdir(parents=True, exist_ok=True)

    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    if sys.platform.startswith("win"):
        os.startfile(str(target))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])

    return {"opened": str(target)}
