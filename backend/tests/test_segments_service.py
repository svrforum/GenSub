from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus
from app.services.segments import (
    load_segments,
    replace_all_segments,
    search_and_replace,
    update_segment,
)
from app.services.subtitles import SegmentData


def _engine(tmp_path):
    e = create_db_engine(f"sqlite:///{tmp_path/'s.db'}")
    init_db(e)
    return e


def _mk_job(engine, job_id="j"):
    with Session(engine) as s:
        s.add(
            Job(
                id=job_id,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()


def test_replace_all_and_load(tmp_path):
    engine = _engine(tmp_path)
    _mk_job(engine)
    segs = [
        SegmentData(idx=0, start=0.0, end=2.0, text="hi"),
        SegmentData(idx=1, start=2.0, end=4.0, text="there"),
    ]
    replace_all_segments(engine, "j", segs)
    loaded = load_segments(engine, "j")
    assert [s.text for s in loaded] == ["hi", "there"]


def test_update_segment_marks_edited(tmp_path):
    engine = _engine(tmp_path)
    _mk_job(engine)
    replace_all_segments(
        engine,
        "j",
        [SegmentData(idx=0, start=0.0, end=1.0, text="hi")],
    )
    update_segment(engine, "j", 0, text="hello", start=0.1, end=1.2)
    loaded = load_segments(engine, "j")
    assert loaded[0].text == "hello"
    assert loaded[0].start == 0.1
    assert loaded[0].end == 1.2


def test_search_and_replace_counts(tmp_path):
    engine = _engine(tmp_path)
    _mk_job(engine)
    replace_all_segments(
        engine,
        "j",
        [
            SegmentData(idx=0, start=0.0, end=1.0, text="트렌스포머"),
            SegmentData(idx=1, start=1.0, end=2.0, text="트렌스포머 이야기"),
            SegmentData(idx=2, start=2.0, end=3.0, text="그 외 내용"),
        ],
    )
    n = search_and_replace(engine, "j", find="트렌스포머", replace="트랜스포머")
    assert n == 2
    loaded = load_segments(engine, "j")
    assert loaded[0].text == "트랜스포머"
    assert loaded[1].text == "트랜스포머 이야기"
