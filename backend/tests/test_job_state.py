from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus
from app.services.job_state import (
    claim_next_pending_job,
    is_cancel_requested,
    mark_failed,
    update_progress,
    update_status,
)


def _engine(tmp_path):
    e = create_db_engine(f"sqlite:///{tmp_path/'ws.db'}")
    init_db(e)
    return e


def _mk(engine, jid, st=JobStatus.pending):
    with Session(engine) as s:
        s.add(
            Job(
                id=jid,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=st,
                progress=0.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()


def test_claim_next_pending_returns_pending_and_marks_downloading(tmp_path):
    engine = _engine(tmp_path)
    _mk(engine, "a", JobStatus.ready)
    _mk(engine, "b", JobStatus.pending)
    _mk(engine, "c", JobStatus.pending)

    claimed = claim_next_pending_job(engine)
    assert claimed is not None
    assert claimed.id in ("b", "c")

    with Session(engine) as s:
        job = s.get(Job, claimed.id)
        assert job.status == JobStatus.downloading


def test_claim_returns_none_when_no_pending(tmp_path):
    engine = _engine(tmp_path)
    _mk(engine, "a", JobStatus.ready)
    assert claim_next_pending_job(engine) is None


def test_update_progress_and_status(tmp_path):
    engine = _engine(tmp_path)
    _mk(engine, "x", JobStatus.downloading)
    update_progress(engine, "x", 0.5, "음성을 듣고 있어요")
    update_status(engine, "x", JobStatus.transcribing)
    with Session(engine) as s:
        job = s.get(Job, "x")
        assert job.progress == 0.5
        assert job.stage_message == "음성을 듣고 있어요"
        assert job.status == JobStatus.transcribing


def test_mark_failed_records_error(tmp_path):
    engine = _engine(tmp_path)
    _mk(engine, "y", JobStatus.downloading)
    mark_failed(engine, "y", "boom")
    with Session(engine) as s:
        job = s.get(Job, "y")
        assert job.status == JobStatus.failed
        assert job.error_message == "boom"


def test_is_cancel_requested(tmp_path):
    engine = _engine(tmp_path)
    _mk(engine, "z", JobStatus.downloading)
    assert is_cancel_requested(engine, "z") is False
    with Session(engine) as s:
        job = s.get(Job, "z")
        job.cancel_requested = True
        s.add(job)
        s.commit()
    assert is_cancel_requested(engine, "z") is True
