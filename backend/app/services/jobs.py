import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.settings import Settings
from app.models.job import Job, JobStatus, SourceKind
from app.services.memo import delete_memos_for_job as _delete_memos_for_job


def create_job_from_url(
    engine: Engine,
    settings: Settings,
    url: str,
    model: str,
    language: str | None,
    initial_prompt: str | None,
) -> Job:
    now = datetime.now(UTC)
    job = Job(
        id=uuid4().hex,
        source_url=url,
        source_kind=SourceKind.url.value,
        model_name=model,
        language=language,
        initial_prompt=initial_prompt,
        status=JobStatus.pending,
        progress=0.0,
        stage_message="준비하고 있어요",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=settings.job_ttl_hours),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
        s.refresh(job)
    return job


def create_job_from_upload(
    engine: Engine,
    settings: Settings,
    filename: str,
    model: str,
    language: str | None,
    initial_prompt: str | None,
) -> tuple[Job, Path]:
    now = datetime.now(UTC)
    job_id = uuid4().hex
    suffix = Path(filename).suffix or ".mp4"
    job_dir = settings.media_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / f"source{suffix}"

    job = Job(
        id=job_id,
        source_url=None,
        source_kind=SourceKind.upload.value,
        title=filename,
        model_name=model,
        language=language,
        initial_prompt=initial_prompt,
        status=JobStatus.pending,
        progress=0.0,
        stage_message="준비하고 있어요",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=settings.job_ttl_hours),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
        s.refresh(job)
    return job, dest


def get_job(engine: Engine, job_id: str) -> Job | None:
    with Session(engine) as s:
        return s.get(Job, job_id)


def job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "source_url": job.source_url,
        "source_kind": job.source_kind,
        "title": job.title,
        "duration_sec": job.duration_sec,
        "language": job.language,
        "model_name": job.model_name,
        "status": job.status.value if hasattr(job.status, "value") else job.status,
        "progress": job.progress,
        "stage_message": job.stage_message,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "expires_at": job.expires_at.isoformat(),
        "cancel_requested": job.cancel_requested,
        "pinned": job.pinned,
    }


def list_recent_jobs(engine: Engine, limit: int = 20) -> list[Job]:
    """만료되지 않은 최근 작업 리스트. pinned 우선, 그다음 updated_at 내림차순."""
    from sqlmodel import select

    now = datetime.now(UTC)
    with Session(engine) as session:
        stmt = (
            select(Job)
            .where(Job.expires_at > now)
            .order_by(Job.pinned.desc(), Job.updated_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        result = session.exec(stmt)
        return list(result.all())


def request_cancel(engine: Engine, job_id: str) -> bool:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return False
        job.cancel_requested = True
        job.updated_at = datetime.now(UTC)
        s.add(job)
        s.commit()
        return True


def delete_job(engine: Engine, settings: Settings, job_id: str) -> bool:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return False
        s.delete(job)
        s.commit()

    # Memo cascade (Job 삭제 후에 — FK 없으므로 순서는 무관하지만 명확성을 위해 뒤)
    _delete_memos_for_job(engine, job_id)

    job_dir = settings.media_dir / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    return True


def toggle_pin(engine: Engine, job_id: str) -> bool | None:
    """pinned 값을 토글. 새 pinned 상태 반환. job이 없으면 None."""
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return None
        job.pinned = not job.pinned
        job.updated_at = datetime.now(UTC)
        s.add(job)
        s.commit()
        return job.pinned


def request_burn(engine: Engine, job_id: str) -> None:
    """ready 또는 done 상태의 job을 burning으로 전이.

    Raises:
        LookupError: job이 존재하지 않음.
        ValueError: job이 ready/done 상태가 아님.
    """
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            raise LookupError(job_id)
        if job.status not in (JobStatus.ready, JobStatus.done):
            raise ValueError(f"cannot burn from status {job.status.value}")
        job.status = JobStatus.burning
        job.progress = 0.0
        job.stage_message = "자막을 영상에 입히고 있어요"
        job.error_message = None
        job.updated_at = datetime.now(UTC)
        s.add(job)
        s.commit()
