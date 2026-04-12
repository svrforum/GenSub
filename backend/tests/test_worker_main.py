from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.downloader import DownloadResult
from app.services.subtitles import SegmentData
from app.services.transcriber import TranscribeResult


def test_worker_tick_picks_pending_and_processes(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    settings = Settings(database_url=f"sqlite:///{tmp_path/'w.db'}")
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    jid = "wj"
    with Session(engine) as s:
        s.add(
            Job(
                id=jid,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.pending,
                progress=0.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()

    media = settings.media_dir / jid
    media.mkdir(parents=True, exist_ok=True)
    (media / "source.mp4").write_bytes(b"0")
    (media / "audio.wav").write_bytes(b"0")

    with (
        patch(
            "app.services.pipeline.download_video",
            return_value=DownloadResult(
                path=media / "source.mp4", title="x", duration=5.0
            ),
        ),
        patch(
            "app.services.pipeline.extract_audio",
            return_value=media / "audio.wav",
        ),
        patch(
            "app.services.pipeline.transcribe",
            return_value=TranscribeResult(
                segments=[SegmentData(idx=0, start=0.0, end=1.0, text="x")],
                language="en",
                duration=5.0,
            ),
        ),
    ):
        from worker.main import tick

        did = tick(settings, engine)
        assert did is True

    with Session(engine) as s:
        job = s.get(Job, jid)
        assert job.status == JobStatus.ready


def test_worker_tick_no_job_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    settings = Settings(database_url=f"sqlite:///{tmp_path/'w2.db'}")
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    from worker.main import tick

    assert tick(settings, engine) is False
