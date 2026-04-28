from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.search import SearchHit, search_all


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def test_empty_query_returns_empty_list(engine):
    assert search_all(engine, "") == []
    assert search_all(engine, "   ") == []


def _make_job(engine, jid: str, title: str):
    job = Job(
        id=jid,
        source_url=f"https://e/{jid}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title=title,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()


def _make_segment(engine, jid: str, idx: int, text: str):
    with Session(engine) as session:
        session.add(Segment(
            job_id=jid, idx=idx,
            start=float(idx), end=float(idx) + 1,
            text=text,
        ))
        session.commit()


def _make_memo(engine, jid: str, idx: int, memo_text: str, snap_text: str):
    with Session(engine) as session:
        m = Memo(
            job_id=jid, segment_idx=idx,
            memo_text=memo_text,
            segment_text_snapshot=snap_text,
            segment_start=float(idx), segment_end=float(idx) + 1,
            job_title_snapshot="t",
        )
        session.add(m)
        session.commit()


def test_matches_segment_text(engine):
    _make_job(engine, "j1", "Test Video")
    _make_segment(engine, "j1", 0, "Hello world")
    _make_segment(engine, "j1", 1, "Goodbye sky")

    hits = search_all(engine, "Hello")
    assert len(hits) == 1
    assert hits[0].kind == "segment"
    assert hits[0].segment_text == "Hello world"
    assert hits[0].segment_idx == 0
    assert hits[0].job_id == "j1"
    assert hits[0].job_title == "Test Video"


def test_matches_memo_text(engine):
    _make_job(engine, "j1", "T")
    _make_segment(engine, "j1", 0, "abc")
    _make_memo(engine, "j1", 0, memo_text="중요한 표현", snap_text="abc")

    hits = search_all(engine, "중요")
    assert len(hits) == 1
    assert hits[0].kind == "memo"
    assert hits[0].memo_text == "중요한 표현"


def test_matches_job_title(engine):
    _make_job(engine, "j1", "영화 추천 모음")
    _make_segment(engine, "j1", 0, "unrelated text")

    hits = search_all(engine, "영화")
    assert len(hits) == 1
    assert hits[0].kind == "job"
    assert hits[0].job_title == "영화 추천 모음"


def test_korean_substring(engine):
    _make_job(engine, "j1", "T")
    _make_segment(engine, "j1", 0, "안녕하세요 반갑습니다")

    hits = search_all(engine, "안녕")
    assert len(hits) == 1
    assert hits[0].kind == "segment"


def test_case_insensitive_ascii(engine):
    _make_job(engine, "j1", "T")
    _make_segment(engine, "j1", 0, "Hello World")

    hits = search_all(engine, "hello")
    assert len(hits) == 1


def test_respects_limit(engine):
    _make_job(engine, "j1", "T")
    for i in range(10):
        _make_segment(engine, "j1", i, f"hello {i}")

    hits = search_all(engine, "hello", limit=3)
    assert len(hits) == 3


def test_excludes_orphan_segments(engine):
    """Job 없는 segment는 결과에서 제외 (defensive INNER JOIN).

    실제 환경은 FK 제약으로 orphan이 발생하지 않지만, INNER JOIN의
    방어적 동작을 확인하기 위해 FK를 일시적으로 끄고 orphan 행을 삽입한다.
    """
    from sqlalchemy import text as sql_text

    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.execute(
            sql_text(
                "INSERT INTO segment (job_id, idx, start, \"end\", text, edited) "
                "VALUES ('ghost', 0, 0, 1, 'hello orphan', 0)"
            )
        )
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    hits = search_all(engine, "hello")
    assert hits == []


def test_groups_results_in_order_job_memo_segment(engine):
    _make_job(engine, "j1", "Search me")
    _make_segment(engine, "j1", 0, "search me too")
    _make_memo(engine, "j1", 0, memo_text="search me note", snap_text="search me too")

    hits = search_all(engine, "search me")
    kinds = [h.kind for h in hits]
    assert kinds == ["job", "memo", "segment"]
