from __future__ import annotations

import logging
import subprocess
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.utils.filenames import sanitize_stem, unique_output_path


logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Raised when a PDF -> Markdown conversion cannot be completed."""

    def __init__(
        self,
        user_message: str,
        *,
        detail: str | None = None,
        code: str = "conversion_failed",
        next_step: str | None = None,
    ):
        super().__init__(detail or user_message)
        self.user_message = user_message
        self.detail = detail
        self.code = code
        self.next_step = next_step


@dataclass
class ConversionResult:
    markdown_path: Path
    source_name: str


def convert_pdf_to_markdown(
    pdf_path: Path,
    *,
    output_dir: Path,
    original_name: str | None = None,
) -> ConversionResult:
    """
    Convert a single PDF into Markdown using OpenDataLoader.

    - `pdf_path` is the PDF on disk (already saved by the caller).
    - `output_dir` is the final folder that keeps the Markdown result.
    - `original_name` is the user-visible filename; used for naming the .md output.
      Falls back to pdf_path.name.

    Raises ConversionError with a human-friendly message on failure.
    """
    if not pdf_path.exists():
        raise ConversionError(
            "업로드된 PDF를 찾을 수 없습니다. 다시 시도해 주세요.",
            detail=f"pdf_path missing: {pdf_path}",
            code="upload_missing",
            next_step="같은 PDF 파일을 다시 업로드해 주세요.",
        )
    if pdf_path.suffix.lower() != ".pdf":
        raise ConversionError(
            "PDF 파일만 변환할 수 있습니다.",
            detail=f"unsupported suffix: {pdf_path.suffix}",
            code="unsupported_file_type",
            next_step="확장자가 .pdf 인 파일만 업로드해 주세요.",
        )

    source_display = original_name or pdf_path.name
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConversionError(
            "결과 폴더를 만들 수 없습니다.",
            detail=f"output_dir mkdir failed for {output_dir}: {exc}",
            code="output_dir_unavailable",
            next_step="출력 폴더 경로와 쓰기 권한을 확인한 뒤 다시 시도해 주세요.",
        ) from exc

    stem = sanitize_stem(Path(source_display).stem)

    with tempfile.TemporaryDirectory(prefix="qmaploader_") as staging_str:
        staging = Path(staging_str)
        staged_pdf = staging / f"{stem}.pdf"
        try:
            shutil.copyfile(pdf_path, staged_pdf)
        except OSError as exc:
            raise ConversionError(
                "임시 작업 파일을 준비할 수 없습니다.",
                detail=f"staging copy failed from {pdf_path} to {staged_pdf}: {exc}",
                code="staging_failed",
                next_step="디스크 공간과 임시 폴더 쓰기 권한을 확인한 뒤 다시 시도해 주세요.",
            ) from exc

        try:
            import opendataloader_pdf  # imported lazily so tests without it still load
        except ImportError as exc:
            raise ConversionError(
                "변환 엔진(OpenDataLoader)이 설치되어 있지 않습니다. 설치를 먼저 완료해 주세요.",
                detail=f"opendataloader_pdf import failed: {exc}",
                code="engine_missing",
                next_step="installer\\install.ps1 를 다시 실행해 OpenDataLoader 설치를 완료해 주세요.",
            ) from exc

        try:
            opendataloader_pdf.convert(
                input_path=[str(staged_pdf)],
                output_dir=str(staging),
                format="markdown",
            )
        except FileNotFoundError as exc:
            logger.warning("OpenDataLoader could not start Java for %s: %s", source_display, exc)
            raise ConversionError(
                "Java를 찾을 수 없습니다. Java 11 이상을 설치한 뒤 다시 시도해 주세요.",
                detail=f"java launch failed: {exc}",
                code="java_missing",
                next_step="Java 11 이상을 설치하거나 PATH에 Java가 등록되어 있는지 확인해 주세요.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            logger.exception("OpenDataLoader process failed for %s", source_display)
            detail = exc.output or exc.stderr or exc.stdout or str(exc)
            if "UnsupportedClassVersionError" in detail or "class file version" in detail:
                raise ConversionError(
                    "설치된 Java 버전이 너무 낮습니다. Java 11 이상으로 업데이트한 뒤 다시 시도해 주세요.",
                    detail=f"java version mismatch: {detail}",
                    code="java_version_too_low",
                    next_step="Java를 11 이상 버전으로 업데이트한 뒤 앱을 다시 실행해 주세요.",
                ) from exc
            raise ConversionError(
                "변환에 실패했습니다. PDF가 손상되었거나 지원되지 않는 형식일 수 있습니다.",
                detail=f"opendataloader_pdf.convert error: {detail}",
                code="engine_failed",
                next_step="다른 PDF로 다시 시도해 보거나, 원본 PDF가 정상적으로 열리는지 확인해 주세요.",
            ) from exc
        except Exception as exc:  # engine raises various errors; normalize here
            logger.exception("OpenDataLoader conversion failed for %s", source_display)
            raise ConversionError(
                "변환에 실패했습니다. PDF가 손상되었거나 지원되지 않는 형식일 수 있습니다.",
                detail=f"opendataloader_pdf.convert error: {exc}",
                code="engine_failed",
                next_step="다른 PDF로 다시 시도해 보거나, 원본 PDF가 정상적으로 열리는지 확인해 주세요.",
            ) from exc

        produced = _find_markdown_output(staging, stem)
        if produced is None:
            raise ConversionError(
                "변환 결과 파일을 찾지 못했습니다. PDF 내용을 읽을 수 없는 형식일 수 있습니다.",
                detail=f"no .md produced under {staging}",
                code="result_missing",
                next_step="원본 PDF가 정상적으로 열리는지 확인한 뒤 다른 PDF로 다시 시도해 주세요.",
            )

        try:
            final_path = unique_output_path(output_dir, stem, suffix=".md")
            shutil.move(str(produced), final_path)
        except OSError as exc:
            raise ConversionError(
                "결과 파일을 저장할 수 없습니다.",
                detail=f"final move failed from {produced} into {output_dir}: {exc}",
                code="output_write_failed",
                next_step="결과 폴더 경로와 쓰기 권한을 확인한 뒤 다시 시도해 주세요.",
            ) from exc

    logger.info("converted %s -> %s", source_display, final_path)
    return ConversionResult(markdown_path=final_path, source_name=source_display)


def _find_markdown_output(staging: Path, stem: str) -> Path | None:
    preferred = staging / f"{stem}.md"
    if preferred.exists():
        return preferred
    candidates = sorted(staging.rglob("*.md"))
    return candidates[0] if candidates else None
