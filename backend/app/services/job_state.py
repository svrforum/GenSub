from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models.job import Job, JobStatus


def _now() -> datetime:
    return datetime.now(UTC)


def claim_next_pending_job(engine: Engine) -> Job | None:
    """원자적으로 pending 작업 하나를 집어 downloading으로 전환."""
    with Session(engine) as s:
        # BEGIN IMMEDIATE acquires a write lock before the SELECT,
        # preventing two workers from claiming the same job concurrently.
        s.exec(text("BEGIN IMMEDIATE"))
        try:
            row = s.exec(
                select(Job)
                .where(Job.status == JobStatus.pending)
                .order_by(Job.created_at)
            ).first()
            if row is None:
                s.rollback()
                return None
            row.status = JobStatus.downloading
            row.progress = 0.0
            row.stage_message = "영상을 가져오고 있어요"
            row.updated_at = _now()
            s.add(row)
            s.commit()
            s.refresh(row)
            return row
        except Exception:
            s.rollback()
            raise


def update_progress(
    engine: Engine,
    job_id: str,
    progress: float,
    stage_message: str | None = None,
) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return
        job.progress = max(0.0, min(1.0, progress))
        if stage_message is not None:
            job.stage_message = stage_message
        job.updated_at = _now()
        s.add(job)
        s.commit()


def update_status(
    engine: Engine,
    job_id: str,
    status: JobStatus,
    stage_message: str | None = None,
) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return
        job.status = status
        if stage_message is not None:
            job.stage_message = stage_message
        job.updated_at = _now()
        s.add(job)
        s.commit()


def update_title_and_duration(
    engine: Engine,
    job_id: str,
    title: str | None,
    duration_sec: float | None,
) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return
        if title:
            job.title = title
        if duration_sec is not None:
            job.duration_sec = duration_sec
        job.updated_at = _now()
        s.add(job)
        s.commit()


def update_language(engine: Engine, job_id: str, language: str) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return
        job.language = language
        job.updated_at = _now()
        s.add(job)
        s.commit()


def mark_failed(engine: Engine, job_id: str, error_message: str) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.failed
        job.error_message = error_message
        job.updated_at = _now()
        s.add(job)
        s.commit()


def mark_ready(engine: Engine, job_id: str) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.ready
        job.progress = 1.0
        job.stage_message = "준비됐어요"
        job.updated_at = _now()
        s.add(job)
        s.commit()


def mark_done(engine: Engine, job_id: str) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.done
        job.progress = 1.0
        job.stage_message = "완료됐어요"
        job.updated_at = _now()
        s.add(job)
        s.commit()


def is_cancel_requested(engine: Engine, job_id: str) -> bool:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        return bool(job and job.cancel_requested)
