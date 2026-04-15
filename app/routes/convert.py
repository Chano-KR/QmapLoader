from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.converter import ConversionError, convert_pdf_to_markdown
from app.services.job_store import Job, JobStore, get_job_store


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["convert"])


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    source_name: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    source_name: str
    markdown_filename: str | None = None
    user_error: str | None = None
    error_code: str | None = None
    next_step: str | None = None


def _to_status_response(job: Job) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        source_name=job.source_name,
        markdown_filename=job.markdown_path.name if job.markdown_path else None,
        user_error=job.user_error,
        error_code=job.error_code,
        next_step=job.next_step,
    )


def _run_conversion(
    job_id: str,
    upload_path: Path,
    source_name: str,
    output_dir: Path,
    store: JobStore,
) -> None:
    store.mark_running(job_id)
    try:
        result = convert_pdf_to_markdown(
            upload_path,
            output_dir=output_dir,
            original_name=source_name,
        )
        store.mark_done(job_id, result.markdown_path)
    except ConversionError as exc:
        logger.warning(
            "job %s failed [%s]: %s | next=%s | detail=%s",
            job_id,
            exc.code,
            exc.user_message,
            exc.next_step,
            exc.detail,
        )
        store.mark_failed(
            job_id,
            exc.user_message,
            detail=exc.detail,
            error_code=exc.code,
            next_step=exc.next_step,
        )
    except Exception as exc:  # pragma: no cover - defensive catch-all
        logger.exception("job %s crashed", job_id)
        store.mark_failed(
            job_id,
            "예상하지 못한 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            detail=repr(exc),
            error_code="internal_error",
            next_step="앱을 다시 실행한 뒤 다시 시도해 주세요. 같은 문제가 반복되면 로그를 확인해 주세요.",
        )
    finally:
        try:
            upload_path.unlink(missing_ok=True)
        except OSError:
            logger.debug("could not remove upload %s", upload_path)


@router.post("/convert", response_model=JobCreatedResponse, status_code=202)
async def submit_conversion(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> JobCreatedResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일 이름이 비어 있습니다.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    tmp_dir = settings.resolved_tmp_dir()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    upload_path = tmp_dir / f"{uuid.uuid4().hex}.pdf"

    try:
        with upload_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        file.file.close()

    job = store.create(source_name=file.filename)
    background_tasks.add_task(
        _run_conversion,
        job.id,
        upload_path,
        file.filename,
        settings.resolved_output_dir(),
        store,
    )

    return JobCreatedResponse(job_id=job.id, status=job.status, source_name=job.source_name)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> JobStatusResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다.")
    return _to_status_response(job)


@router.get("/jobs/{job_id}/result")
def download_result(
    job_id: str,
    store: JobStore = Depends(get_job_store),
):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다.")
    if job.status != "done" or job.markdown_path is None:
        return JSONResponse(
            status_code=409,
            content={"detail": "아직 변환이 완료되지 않았습니다.", "status": job.status},
        )
    if not job.markdown_path.exists():
        raise HTTPException(status_code=410, detail="결과 파일이 더 이상 존재하지 않습니다.")
    return FileResponse(
        path=job.markdown_path,
        media_type="text/markdown; charset=utf-8",
        filename=job.markdown_path.name,
    )
