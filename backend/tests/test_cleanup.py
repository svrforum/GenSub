from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.cleanup import purge_expired_jobs, sweep_zombie_jobs


def _make_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return Settings(database_url=f"sqlite:///{tmp_path/'c.db'}")


def test_sweep_zombie_jobs_marks_in_progress_as_failed(tmp_path, monkeypatch):
    settings = _make_settings(tmp_path, monkeypatch)
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    now = datetime.now(UTC)
    with Session(engine) as s:
        for i, st in enumerate(
            [JobStatus.downloading, JobStatus.transcribing, JobStatus.burning, JobStatus.ready]
        ):
            s.add(
                Job(
                    id=f"j{i}",
                    source_kind="url",
                    source_url="https://y/x",
                    model_name="small",
                    status=st,
                    progress=0.5,
                    expires_at=now + timedelta(hours=1),
                )
            )
        s.commit()

    n = sweep_zombie_jobs(engine)
    assert n == 3

    with Session(engine) as s:
        assert s.get(Job, "j0").status == JobStatus.failed
        assert s.get(Job, "j3").status == JobStatus.ready


def test_purge_expired_jobs_deletes_db_and_dir(tmp_path, monkeypatch):
    settings = _make_settings(tmp_path, monkeypatch)
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    now = datetime.now(UTC)
    with Session(engine) as s:
        s.add(
            Job(
                id="old",
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                expires_at=now - timedelta(hours=1),
            )
        )
        s.add(
            Job(
                id="new",
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                expires_at=now + timedelta(hours=1),
            )
        )
        s.commit()

    job_dir = settings.media_dir / "old"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "a.txt").write_text("x")

    n = purge_expired_jobs(engine, settings)
    assert n == 1
    assert not job_dir.exists()

    with Session(engine) as s:
        assert s.get(Job, "old") is None
        assert s.get(Job, "new") is not None
