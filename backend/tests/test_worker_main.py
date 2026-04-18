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


def test_worker_tick_picks_burn_job_before_pending(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    settings = Settings(database_url=f"sqlite:///{tmp_path/'wb.db'}")
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    burn_id = "burn1"
    pending_id = "pend1"
    with Session(engine) as s:
        s.add(
            Job(
                id=burn_id,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.burning,
                progress=0.0,
                duration_sec=5.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.add(
            Job(
                id=pending_id,
                source_kind="url",
                source_url="https://y/y",
                model_name="small",
                status=JobStatus.pending,
                progress=0.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()

    burn_media = settings.media_dir / burn_id
    burn_media.mkdir(parents=True, exist_ok=True)
    (burn_media / "source.mp4").write_bytes(b"0")

    # Seed at least one segment so srt_segments_to_ass has something to write.
    from app.services.segments import replace_all_segments
    from app.services.subtitles import SegmentData

    replace_all_segments(
        engine, burn_id, [SegmentData(idx=0, start=0.0, end=1.0, text="hi")]
    )

    with patch("app.services.pipeline.burn_video") as mock_burn:
        def _fake(video, ass, output, total_duration_sec, progress_callback=None):
            output.write_bytes(b"burned")
            return output

        mock_burn.side_effect = _fake

        from worker.main import tick

        did = tick(settings, engine)
        assert did is True

    with Session(engine) as s:
        burn_job = s.get(Job, burn_id)
        pending_job = s.get(Job, pending_id)
        # The burn job was picked and completed this tick
        assert burn_job.status == JobStatus.done
        # The pending job is still pending — burn had priority, took this tick
        assert pending_job.status == JobStatus.pending
