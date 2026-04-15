from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

import app.services.converter as converter_module
from app.services.converter import ConversionError, convert_pdf_to_markdown


class _FakeTempDir:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> str:
        if self.path.exists():
            import shutil
            shutil.rmtree(self.path)
        self.path.mkdir(parents=True)
        return str(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        import shutil
        shutil.rmtree(self.path, ignore_errors=True)


def _patch_tempdir(monkeypatch: pytest.MonkeyPatch, base_path: Path) -> None:
    monkeypatch.setattr(
        converter_module.tempfile,
        "TemporaryDirectory",
        lambda prefix="qmaploader_": _FakeTempDir(base_path / "staging"),
    )


def test_raises_when_pdf_missing(tmp_path: Path):
    missing = tmp_path / "nope.pdf"
    with pytest.raises(ConversionError) as exc:
        convert_pdf_to_markdown(missing, output_dir=tmp_path / "out")
    assert "찾을 수 없습니다" in exc.value.user_message


def test_raises_on_non_pdf_suffix(tmp_path: Path):
    fake = tmp_path / "file.txt"
    fake.write_text("not a pdf")
    with pytest.raises(ConversionError) as exc:
        convert_pdf_to_markdown(fake, output_dir=tmp_path / "out")
    assert "PDF" in exc.value.user_message


def test_raises_clear_error_when_java_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _patch_tempdir(monkeypatch, tmp_path)

    stub = types.SimpleNamespace()

    def _convert(**kwargs):
        raise FileNotFoundError(2, "The system cannot find the file specified", "java")

    stub.convert = _convert
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", stub)

    with pytest.raises(ConversionError) as exc:
        convert_pdf_to_markdown(pdf, output_dir=tmp_path / "out")

    assert "Java를 찾을 수 없습니다" in exc.value.user_message
    assert exc.value.code == "java_missing"
    assert exc.value.next_step


def test_raises_clear_error_when_java_version_too_low(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _patch_tempdir(monkeypatch, tmp_path)

    stub = types.SimpleNamespace()

    def _convert(**kwargs):
        raise subprocess.CalledProcessError(
            1,
            ["java", "-jar", "fake.jar"],
            output="UnsupportedClassVersionError: class file version 61.0",
        )

    stub.convert = _convert
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", stub)

    with pytest.raises(ConversionError) as exc:
        convert_pdf_to_markdown(pdf, output_dir=tmp_path / "out")

    assert "Java 11 이상" in exc.value.user_message
    assert exc.value.code == "java_version_too_low"


def test_raises_when_markdown_result_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _patch_tempdir(monkeypatch, tmp_path)

    stub = types.SimpleNamespace()
    stub.convert = lambda **kwargs: None
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", stub)

    with pytest.raises(ConversionError) as exc:
        convert_pdf_to_markdown(pdf, output_dir=tmp_path / "out")

    assert exc.value.code == "result_missing"
    assert "결과 파일" in exc.value.user_message


def test_raises_when_output_dir_cannot_be_created(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    original_mkdir = Path.mkdir
    blocked = tmp_path / "blocked"

    def _mkdir(self, *args, **kwargs):
        if self == blocked:
            raise PermissionError("blocked")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", _mkdir)

    with pytest.raises(ConversionError) as exc:
        convert_pdf_to_markdown(pdf, output_dir=blocked)

    assert exc.value.code == "output_dir_unavailable"
    assert "결과 폴더" in exc.value.user_message


def test_raises_generic_engine_failure_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _patch_tempdir(monkeypatch, tmp_path)

    stub = types.SimpleNamespace()

    def _convert(**kwargs):
        raise RuntimeError("unexpected parser crash")

    stub.convert = _convert
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", stub)

    with pytest.raises(ConversionError) as exc:
        convert_pdf_to_markdown(pdf, output_dir=tmp_path / "out")

    assert exc.value.code == "engine_failed"
    assert "변환에 실패했습니다" in exc.value.user_message
