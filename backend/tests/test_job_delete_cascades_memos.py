from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.services.jobs import delete_job
from app.services.memo import list_memos_for_job


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


@pytest.fixture
def settings(tmp_path):
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'jobs.db'}",
        media_dir=tmp_path / "media",
        model_cache_dir=tmp_path / "models",
    )


def _seed_job_with_memos(engine, job_id="job1"):
    job = Job(
        id=job_id,
        source_url="https://e/1",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title="T",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        for i in range(3):
            session.add(Memo(
                job_id=job_id, segment_idx=i,
                memo_text=f"note {i}",
                segment_text_snapshot=f"s{i}",
                segment_start=float(i), segment_end=float(i) + 1,
            ))
        session.commit()


def test_delete_job_cascades_memos(engine, settings):
    _seed_job_with_memos(engine)
    _seed_job_with_memos(engine, job_id="job2")

    ok = delete_job(engine, settings, "job1")
    assert ok is True
    assert list_memos_for_job(engine, "job1") == []
    # 다른 Job의 메모는 보존
    assert len(list_memos_for_job(engine, "job2")) == 3


def test_delete_missing_job_does_not_raise(engine, settings):
    ok = delete_job(engine, settings, "nonexistent")
    assert ok is False
