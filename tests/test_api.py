from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services import converter as converter_module
from app.services.converter import ConversionError, ConversionResult
from app.services.job_store import get_job_store


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "output_dir", str(tmp_path / "out"))
    monkeypatch.setattr(settings, "tmp_dir", str(tmp_path / "tmp"))

    app = create_app()
    with TestClient(app) as c:
        yield c


def _stub_success(pdf_path: Path, *, output_dir: Path, original_name: str | None = None):
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{Path(original_name or pdf_path.name).stem}.md"
    out.write_text("# stub", encoding="utf-8")
    return ConversionResult(markdown_path=out, source_name=original_name or pdf_path.name)


def _stub_failure(pdf_path: Path, *, output_dir: Path, original_name: str | None = None):
    raise ConversionError(
        "Java를 찾을 수 없습니다. Java 11 이상을 설치한 뒤 다시 시도해 주세요.",
        detail="java launch failed",
        code="java_missing",
        next_step="Java 11 이상을 설치하거나 PATH에 Java가 등록되어 있는지 확인해 주세요.",
    )


def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "output_dir" in body


def test_rejects_non_pdf_upload(client: TestClient):
    response = client.post(
        "/api/convert",
        files={"file": ("notes.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    assert response.status_code == 400


def test_full_convert_flow_with_stub(client: TestClient, monkeypatch):
    monkeypatch.setattr(converter_module, "convert_pdf_to_markdown", _stub_success)
    # route imports the symbol directly, so patch there as well
    from app.routes import convert as convert_route
    monkeypatch.setattr(convert_route, "convert_pdf_to_markdown", _stub_success)

    response = client.post(
        "/api/convert",
        files={"file": ("sample.pdf", io.BytesIO(b"%PDF-1.4 dummy"), "application/pdf")},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "done"
    assert status["markdown_filename"] == "sample.md"

    result = client.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200
    assert "stub" in result.text


def test_status_for_unknown_job(client: TestClient):
    response = client.get("/api/jobs/does-not-exist")
    assert response.status_code == 404


def test_result_before_done_returns_409(client: TestClient):
    store = get_job_store()
    job = store.create(source_name="pending.pdf")
    response = client.get(f"/api/jobs/{job.id}/result")
    assert response.status_code == 409


def test_failed_job_exposes_error_code_and_next_step(client: TestClient, monkeypatch):
    monkeypatch.setattr(converter_module, "convert_pdf_to_markdown", _stub_failure)
    from app.routes import convert as convert_route
    monkeypatch.setattr(convert_route, "convert_pdf_to_markdown", _stub_failure)

    response = client.post(
        "/api/convert",
        files={"file": ("sample.pdf", io.BytesIO(b"%PDF-1.4 dummy"), "application/pdf")},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "java_missing"
    assert "Java를 찾을 수 없습니다" in body["user_error"]
    assert "PATH" in body["next_step"]
