from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.settings import Settings
from app.models.job import Job, JobStatus, SourceKind


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
