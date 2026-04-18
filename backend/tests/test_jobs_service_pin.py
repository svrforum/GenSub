from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.services.jobs import toggle_pin


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


@pytest.fixture
def ready_job_id(engine) -> str:
    job = Job(
        id="j1",
        source_url="https://example.com/v",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
    return "j1"


def test_toggle_pin_from_false_returns_true(engine, ready_job_id):
    with Session(engine) as s:
        assert s.get(Job, ready_job_id).pinned is False
    result = toggle_pin(engine, ready_job_id)
    assert result is True
    with Session(engine) as s:
        got = s.get(Job, ready_job_id)
        assert got.pinned is True


def test_toggle_pin_from_true_returns_false(engine, ready_job_id):
    toggle_pin(engine, ready_job_id)  # -> True
    result = toggle_pin(engine, ready_job_id)  # -> False
    assert result is False
    with Session(engine) as s:
        got = s.get(Job, ready_job_id)
        assert got.pinned is False


def test_toggle_pin_missing_returns_none(engine):
    result = toggle_pin(engine, "nonexistent")
    assert result is None
