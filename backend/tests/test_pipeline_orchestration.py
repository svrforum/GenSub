from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.downloader import DownloadResult
from app.services.pipeline import process_job
from app.services.subtitles import SegmentData
from app.services.transcriber import TranscribeResult


def _make(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    settings = Settings(database_url=f"sqlite:///{tmp_path/'p.db'}")
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    return settings, engine


def test_process_job_happy_path(tmp_path, monkeypatch):
    settings, engine = _make(tmp_path, monkeypatch)
    job_id = "j1"
    with Session(engine) as s:
        s.add(
            Job(
                id=job_id,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.downloading,
                progress=0.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()

    media = settings.media_dir / job_id
    media.mkdir(parents=True, exist_ok=True)
    fake_source = media / "source.mp4"
    fake_source.write_bytes(b"0")
    fake_audio = media / "audio.wav"
    fake_audio.write_bytes(b"0")

    with (
        patch(
            "app.services.pipeline.download_video",
            return_value=DownloadResult(path=fake_source, title="t", duration=10.0),
        ),
        patch(
            "app.services.pipeline.extract_audio",
            return_value=fake_audio,
        ),
        patch(
            "app.services.pipeline.transcribe",
            return_value=TranscribeResult(
                segments=[SegmentData(idx=0, start=0.0, end=3.0, text="hi")],
                language="en",
                duration=10.0,
            ),
        ),
    ):
        process_job(settings=settings, engine=engine, job_id=job_id)

    with Session(engine) as s:
        job = s.get(Job, job_id)
        assert job.status == JobStatus.ready
        assert job.language == "en"
        assert job.duration_sec == 10.0

    assert (media / "subtitles.srt").exists()
    assert (media / "subtitles.vtt").exists()


def test_process_job_failure_marks_failed(tmp_path, monkeypatch):
    settings, engine = _make(tmp_path, monkeypatch)
    job_id = "j2"
    with Session(engine) as s:
        s.add(
            Job(
                id=job_id,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.downloading,
                progress=0.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()

    with patch(
        "app.services.pipeline.download_video",
        side_effect=RuntimeError("video unavailable"),
    ):
        process_job(settings=settings, engine=engine, job_id=job_id)

    with Session(engine) as s:
        job = s.get(Job, job_id)
        assert job.status == JobStatus.failed
        assert "video unavailable" in (job.error_message or "")
