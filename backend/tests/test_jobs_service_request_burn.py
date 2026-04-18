from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.services.jobs import request_burn


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def _make_job(engine, status: JobStatus) -> str:
    job_id = "j1"
    job = Job(
        id=job_id,
        source_url="https://example.com/v",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=status,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
    return job_id


def test_request_burn_from_ready_transitions_to_burning(engine):
    jid = _make_job(engine, JobStatus.ready)
    request_burn(engine, jid)
    with Session(engine) as s:
        got = s.get(Job, jid)
        assert got.status == JobStatus.burning
        assert got.progress == 0.0
        assert got.stage_message is not None


def test_request_burn_from_done_transitions_to_burning(engine):
    """burn은 ready와 done 양쪽에서 허용 (재-burn 시나리오)."""
    jid = _make_job(engine, JobStatus.done)
    request_burn(engine, jid)
    with Session(engine) as s:
        got = s.get(Job, jid)
        assert got.status == JobStatus.burning


def test_request_burn_from_transcribing_raises_value_error(engine):
    jid = _make_job(engine, JobStatus.transcribing)
    with pytest.raises(ValueError):
        request_burn(engine, jid)


def test_request_burn_missing_raises_lookup_error(engine):
    with pytest.raises(LookupError):
        request_burn(engine, "nonexistent")
