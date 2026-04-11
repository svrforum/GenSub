import shutil
from datetime import UTC, datetime

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.settings import Settings
from app.models.job import Job, JobStatus

ACTIVE_STATES = {JobStatus.downloading, JobStatus.transcribing, JobStatus.burning}


def sweep_zombie_jobs(engine: Engine) -> int:
    now = datetime.now(UTC)
    count = 0
    with Session(engine) as s:
        rows = s.exec(
            select(Job).where(Job.status.in_([st.value for st in ACTIVE_STATES]))
        ).all()
        for job in rows:
            job.status = JobStatus.failed
            job.error_message = "컨테이너 재시작으로 인해 중단되었어요"
            job.updated_at = now
            s.add(job)
            count += 1
        s.commit()
    return count


def purge_expired_jobs(engine: Engine, settings: Settings) -> int:
    now = datetime.now(UTC)
    count = 0
    with Session(engine) as s:
        rows = s.exec(select(Job).where(Job.expires_at < now)).all()
        for job in rows:
            job_dir = settings.media_dir / job.id
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)
            s.delete(job)
            count += 1
        s.commit()
    return count
