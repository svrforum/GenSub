from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.pipeline import process_burn_job
from app.services.segments import replace_all_segments
from app.services.subtitles import SegmentData


def test_process_burn_creates_output_and_marks_done(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    settings = Settings(database_url=f"sqlite:///{tmp_path/'b.db'}")
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    job_id = "jb"
    with Session(engine) as s:
        s.add(
            Job(
                id=job_id,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.burning,
                progress=0.0,
                duration_sec=10.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()

    media = settings.media_dir / job_id
    media.mkdir(parents=True, exist_ok=True)
    (media / "source.mp4").write_bytes(b"0")
    replace_all_segments(
        engine, job_id, [SegmentData(idx=0, start=0.0, end=2.0, text="hi")]
    )

    with patch("app.services.pipeline.burn_video") as mock_burn:
        def _fake(
            video,
            ass,
            output,
            total_duration_sec,
            progress_callback=None,
            cancel_check=None,
        ):
            output.write_bytes(b"burned")
            return output
        mock_burn.side_effect = _fake
        process_burn_job(settings=settings, engine=engine, job_id=job_id)

    assert (media / "burned.mp4").exists()
    with Session(engine) as s:
        job = s.get(Job, job_id)
        assert job.status == JobStatus.done
