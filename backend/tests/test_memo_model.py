import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.memo import Memo


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def test_memo_creation_and_persistence(engine):
    memo = Memo(
        job_id="job1",
        segment_idx=0,
        memo_text="test note",
        segment_text_snapshot="hello",
        segment_start=0.0,
        segment_end=1.5,
        job_title_snapshot="Test Video",
    )
    with Session(engine) as session:
        session.add(memo)
        session.commit()
        session.refresh(memo)
        assert memo.id is not None
        assert memo.created_at is not None
        assert memo.updated_at is not None


def test_memo_default_empty_text(engine):
    memo = Memo(
        job_id="job1",
        segment_idx=0,
        segment_text_snapshot="hello",
        segment_start=0.0,
        segment_end=1.5,
    )
    with Session(engine) as session:
        session.add(memo)
        session.commit()
        session.refresh(memo)
        assert memo.memo_text == ""


def test_memo_unique_constraint_on_job_segment(engine):
    from sqlalchemy.exc import IntegrityError

    with Session(engine) as session:
        session.add(Memo(
            job_id="job1", segment_idx=5,
            segment_text_snapshot="a", segment_start=0, segment_end=1,
        ))
        session.commit()

    with Session(engine) as session:
        session.add(Memo(
            job_id="job1", segment_idx=5,
            segment_text_snapshot="b", segment_start=0, segment_end=1,
        ))
        with pytest.raises(IntegrityError):
            session.commit()


def test_memo_allows_same_segment_idx_across_jobs(engine):
    with Session(engine) as session:
        session.add(Memo(
            job_id="job1", segment_idx=0,
            segment_text_snapshot="a", segment_start=0, segment_end=1,
        ))
        session.add(Memo(
            job_id="job2", segment_idx=0,
            segment_text_snapshot="b", segment_start=0, segment_end=1,
        ))
        session.commit()
