from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.services.jobs import list_recent_jobs


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def _insert(engine, jid: str, status: JobStatus, *, pinned=False, expires_in_h=24, offset_min=0):
    now = datetime.now(UTC)
    job = Job(
        id=jid,
        source_url=f"https://example.com/{jid}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=status,
        pinned=pinned,
        expires_at=now + timedelta(hours=expires_in_h),
        updated_at=now - timedelta(minutes=offset_min),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()


def test_list_recent_returns_non_expired(engine):
    _insert(engine, "alive", JobStatus.ready)
    _insert(engine, "expired", JobStatus.ready, expires_in_h=-1)

    jobs = list_recent_jobs(engine)

    ids = {j.id for j in jobs}
    assert "alive" in ids
    assert "expired" not in ids


def test_list_recent_pinned_first(engine):
    _insert(engine, "old_pinned", JobStatus.ready, pinned=True, offset_min=120)
    _insert(engine, "recent_normal", JobStatus.ready, pinned=False, offset_min=5)

    jobs = list_recent_jobs(engine)

    assert jobs[0].id == "old_pinned"
    assert jobs[1].id == "recent_normal"


def test_list_recent_respects_limit(engine):
    for i in range(5):
        _insert(engine, f"j{i}", JobStatus.ready, offset_min=i)

    jobs = list_recent_jobs(engine, limit=3)

    assert len(jobs) == 3


def test_list_recent_empty_when_no_jobs(engine):
    assert list_recent_jobs(engine) == []
