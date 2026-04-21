from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.memo import (
    delete_memo,
    delete_memos_for_job,
    get_memo_by_segment,
    list_memos_for_job,
    update_memo_text,
)


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def _seed(engine, job_id="job1", segment_idxs=(0,), job_title="Test"):
    job = Job(
        id=job_id,
        source_url=f"https://e/{job_id}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title=job_title,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        for idx in segment_idxs:
            session.add(Segment(
                job_id=job_id, idx=idx,
                start=float(idx), end=float(idx) + 1.0,
                text=f"text {idx}",
            ))
        session.commit()


def _make_memo(engine, job_id: str, segment_idx: int, memo_text: str = "") -> Memo:
    with Session(engine) as session:
        memo = Memo(
            job_id=job_id, segment_idx=segment_idx,
            memo_text=memo_text,
            segment_text_snapshot=f"text {segment_idx}",
            segment_start=float(segment_idx),
            segment_end=float(segment_idx) + 1.0,
            job_title_snapshot="Test",
        )
        session.add(memo)
        session.commit()
        session.refresh(memo)
        return memo


def test_get_memo_by_segment_returns_memo(engine):
    _seed(engine)
    m = _make_memo(engine, "job1", 0)
    got = get_memo_by_segment(engine, "job1", 0)
    assert got is not None
    assert got.id == m.id


def test_get_memo_by_segment_returns_none_when_missing(engine):
    _seed(engine)
    assert get_memo_by_segment(engine, "job1", 0) is None


def test_list_memos_for_job_returns_all(engine):
    _seed(engine, segment_idxs=(0, 1, 2))
    _make_memo(engine, "job1", 0)
    _make_memo(engine, "job1", 2)
    _seed(engine, job_id="job2")
    _make_memo(engine, "job2", 0)

    memos = list_memos_for_job(engine, "job1")
    assert len(memos) == 2
    idxs = {m.segment_idx for m in memos}
    assert idxs == {0, 2}


def test_update_memo_text_persists(engine):
    _seed(engine)
    m = _make_memo(engine, "job1", 0)
    updated = update_memo_text(engine, m.id, "new note")
    assert updated is not None
    assert updated.memo_text == "new note"
    assert updated.updated_at >= m.updated_at


def test_update_memo_text_missing_returns_none(engine):
    assert update_memo_text(engine, 99999, "any") is None


def test_delete_memo_removes_row(engine):
    _seed(engine)
    m = _make_memo(engine, "job1", 0)
    ok = delete_memo(engine, m.id)
    assert ok is True
    assert get_memo_by_segment(engine, "job1", 0) is None


def test_delete_memo_missing_returns_false(engine):
    assert delete_memo(engine, 99999) is False


def test_delete_memos_for_job_removes_all_for_job(engine):
    _seed(engine, segment_idxs=(0, 1))
    _make_memo(engine, "job1", 0)
    _make_memo(engine, "job1", 1)
    _seed(engine, job_id="job2")
    _make_memo(engine, "job2", 0)

    n = delete_memos_for_job(engine, "job1")
    assert n == 2
    assert list_memos_for_job(engine, "job1") == []
    assert len(list_memos_for_job(engine, "job2")) == 1
