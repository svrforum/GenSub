from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.memo import toggle_save_memo


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


@pytest.fixture
def job_with_segment(engine):
    job = Job(
        id="job1",
        source_url="https://e/1",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title="Test",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        pinned=False,
    )
    seg = Segment(
        job_id="job1", idx=3,
        start=10.0, end=12.5,
        text="Hello world",
    )
    with Session(engine) as session:
        session.add(job)
        session.add(seg)
        session.commit()
    return job


def test_toggle_creates_memo_when_absent(engine, job_with_segment):
    result = toggle_save_memo(engine, "job1", 3)
    assert result.action == "created"
    assert result.memo is not None
    assert result.memo.memo_text == ""
    assert result.memo.segment_text_snapshot == "Hello world"
    assert result.memo.segment_start == 10.0
    assert result.memo.segment_end == 12.5
    assert result.memo.job_title_snapshot == "Test"


def test_toggle_auto_pins_job_on_create(engine, job_with_segment):
    toggle_save_memo(engine, "job1", 3)
    with Session(engine) as session:
        job = session.get(Job, "job1")
        assert job.pinned is True


def test_toggle_deletes_memo_when_empty_text(engine, job_with_segment):
    toggle_save_memo(engine, "job1", 3)
    result = toggle_save_memo(engine, "job1", 3)
    assert result.action == "deleted"
    assert result.memo is None

    with Session(engine) as session:
        from sqlmodel import select
        result = session.exec(select(Memo).where(Memo.job_id == "job1"))
        assert len(list(result.all())) == 0


def test_toggle_conflict_when_memo_has_text(engine, job_with_segment):
    first = toggle_save_memo(engine, "job1", 3)
    with Session(engine) as session:
        m = session.get(Memo, first.memo.id)
        m.memo_text = "some note"
        session.add(m)
        session.commit()

    result = toggle_save_memo(engine, "job1", 3)
    assert result.action == "conflict"
    assert result.memo is not None
    assert result.memo.memo_text == "some note"


def test_toggle_raises_when_segment_missing(engine, job_with_segment):
    with pytest.raises(LookupError):
        toggle_save_memo(engine, "job1", 999)


def test_toggle_raises_when_job_missing(engine):
    with pytest.raises(LookupError):
        toggle_save_memo(engine, "nonexistent", 0)
