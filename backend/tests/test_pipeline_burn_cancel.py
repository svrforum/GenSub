from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus, SourceKind
from app.services.pipeline import process_burn_job


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'jobs.db'}",
        media_dir=tmp_path / "media",
        model_cache_dir=tmp_path / "models",
    )


def _seed_burning_job(engine, settings: Settings, *, cancel: bool) -> str:
    """burn 준비가 된 Job과 필요한 소스 파일을 세팅."""
    media = settings.media_dir / "j1"
    media.mkdir(parents=True, exist_ok=True)
    (media / "source.mp4").write_bytes(b"fake")  # 실제 ffmpeg 실행 전에 cancel되므로 내용 무관

    job_id = "j1"
    job = Job(
        id=job_id,
        source_url="https://example.com/v",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.burning,
        progress=0.0,
        duration_sec=2.0,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        cancel_requested=cancel,
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
    return job_id


def test_burn_respects_cancel_before_start(tmp_path):
    """cancel_requested=True 상태로 시작하면 ffmpeg 실행 전에 failed 전이."""
    settings = _make_settings(tmp_path)
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    jid = _seed_burning_job(engine, settings, cancel=True)

    process_burn_job(settings=settings, engine=engine, job_id=jid)

    with Session(engine) as s:
        job = s.get(Job, jid)
    assert job.status == JobStatus.failed
    assert job.error_message is not None
    assert "취소" in job.error_message
    # ffmpeg가 실행되지 않았으므로 burned.mp4는 없어야 함
    assert not (settings.media_dir / jid / "burned.mp4").exists()
