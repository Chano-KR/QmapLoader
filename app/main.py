from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes import convert as convert_route
from app.routes import system as system_route
from app.routes import ui as ui_route


def _configure_logging() -> None:
    settings = get_settings()
    logs_dir = settings.logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        file_handler = RotatingFileHandler(
            logs_dir / "qmaploader.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        )
        root.addHandler(file_handler)


def create_app() -> FastAPI:
    _configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="QmapLoader",
        description="Local PDF → Markdown converter wrapping OpenDataLoader.",
        version="0.1.0",
    )

    settings.resolved_output_dir().mkdir(parents=True, exist_ok=True)
    settings.resolved_tmp_dir().mkdir(parents=True, exist_ok=True)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(ui_route.router)
    app.include_router(convert_route.router)
    app.include_router(system_route.router)

    @app.get("/api/info")
    def api_info() -> JSONResponse:
        return JSONResponse(
            {
                "app": "QmapLoader",
                "version": "0.1.0",
                "docs": "/docs",
                "output_dir": str(settings.resolved_output_dir()),
            }
        )

    return app


app = create_app()
