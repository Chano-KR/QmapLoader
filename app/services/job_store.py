from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


JobStatus = Literal["queued", "running", "done", "failed"]


@dataclass
class Job:
    id: str
    source_name: str
    status: JobStatus = "queued"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    markdown_path: Path | None = None
    user_error: str | None = None
    detail: str | None = None
    error_code: str | None = None
    next_step: str | None = None


class JobStore:
    """In-memory job registry. Sufficient for single-user MVP."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, source_name: str) -> Job:
        job = Job(id=uuid.uuid4().hex, source_name=source_name)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        self._update(job_id, status="running")

    def mark_done(self, job_id: str, markdown_path: Path) -> None:
        self._update(job_id, status="done", markdown_path=markdown_path)

    def mark_failed(
        self,
        job_id: str,
        user_error: str,
        detail: str | None = None,
        *,
        error_code: str | None = None,
        next_step: str | None = None,
    ) -> None:
        self._update(
            job_id,
            status="failed",
            user_error=user_error,
            detail=detail,
            error_code=error_code,
            next_step=next_step,
        )

    def _update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = datetime.now()


_store = JobStore()


def get_job_store() -> JobStore:
    return _store
