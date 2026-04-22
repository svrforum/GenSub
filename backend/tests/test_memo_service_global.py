from dataclasses import is_dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.memo import MemoView, list_all_memos_with_liveness


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def _insert_job(engine, job_id: str, title: str):
    job = Job(
        id=job_id,
        source_url=f"https://e/{job_id}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title=title,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()


def _insert_segment(engine, job_id: str, idx: int, text: str):
    with Session(engine) as session:
        session.add(Segment(
            job_id=job_id, idx=idx,
            start=float(idx), end=float(idx) + 1,
            text=text,
        ))
        session.commit()


def _insert_memo(engine, job_id: str, idx: int, snap_text: str, snap_title: str, memo_text: str = "") -> int:
    with Session(engine) as session:
        m = Memo(
            job_id=job_id, segment_idx=idx,
            memo_text=memo_text,
            segment_text_snapshot=snap_text,
            segment_start=float(idx), segment_end=float(idx) + 1,
            job_title_snapshot=snap_title,
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        return m.id


def test_memo_view_is_dataclass():
    assert is_dataclass(MemoView)


def test_list_returns_empty_when_no_memos(engine):
    assert list_all_memos_with_liveness(engine) == []


def test_list_newest_first(engine):
    _insert_job(engine, "job1", "T")
    _insert_segment(engine, "job1", 0, "a")
    _insert_segment(engine, "job1", 1, "b")
    id_a = _insert_memo(engine, "job1", 0, "a", "T")
    import time
    time.sleep(0.01)
    id_b = _insert_memo(engine, "job1", 1, "b", "T")

    items = list_all_memos_with_liveness(engine)
    assert [x.id for x in items] == [id_b, id_a]


def test_list_job_alive_true_when_exists(engine):
    _insert_job(engine, "job1", "T")
    _insert_segment(engine, "job1", 0, "cur")
    _insert_memo(engine, "job1", 0, "snap", "T")

    items = list_all_memos_with_liveness(engine)
    assert len(items) == 1
    assert items[0].job_alive is True


def test_list_uses_current_text_when_available(engine):
    _insert_job(engine, "job1", "Current Title")
    _insert_segment(engine, "job1", 0, "current text")
    _insert_memo(engine, "job1", 0, snap_text="snapshot text", snap_title="Snapshot Title")

    items = list_all_memos_with_liveness(engine)
    assert len(items) == 1
    assert items[0].segment_text == "current text"
    assert items[0].job_title == "Current Title"


def test_list_falls_back_to_snapshot_when_job_missing(engine):
    _insert_memo(engine, "orphan_job", 0, "snap", "snap_title")

    items = list_all_memos_with_liveness(engine)
    assert len(items) == 1
    assert items[0].job_alive is False
    assert items[0].segment_text == "snap"
    assert items[0].job_title == "snap_title"


def test_list_respects_limit(engine):
    _insert_job(engine, "job1", "T")
    for i in range(5):
        _insert_segment(engine, "job1", i, f"s{i}")
        _insert_memo(engine, "job1", i, f"s{i}", "T")

    items = list_all_memos_with_liveness(engine, limit=3)
    assert len(items) == 3
