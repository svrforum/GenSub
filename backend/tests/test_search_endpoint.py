from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "jobs.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    return TestClient(app)


def _seed(client, jid="j1", title="Hello video"):
    engine = client.app.state.engine
    job = Job(
        id=jid,
        source_url=f"https://e/{jid}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title=title,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    seg = Segment(
        job_id=jid, idx=0,
        start=0, end=1,
        text="searchable segment text",
    )
    memo = Memo(
        job_id=jid, segment_idx=0,
        memo_text="searchable memo body",
        segment_text_snapshot="searchable segment text",
        segment_start=0, segment_end=1,
    )
    with Session(engine) as session:
        session.add(job)
        session.add(seg)
        session.add(memo)
        session.commit()


def test_get_search_empty_query(client):
    resp = client.get("/api/search?q=")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_get_search_returns_grouped_results(client):
    _seed(client)
    resp = client.get("/api/search?q=searchable")
    assert resp.status_code == 200
    items = resp.json()["items"]
    kinds = [i["kind"] for i in items]
    assert "memo" in kinds
    assert "segment" in kinds


def test_get_search_response_shape_segment(client):
    _seed(client)
    resp = client.get("/api/search?q=searchable")
    items = resp.json()["items"]
    seg_items = [i for i in items if i["kind"] == "segment"]
    assert len(seg_items) == 1
    s = seg_items[0]
    assert s["job_id"] == "j1"
    assert s["job_title"] == "Hello video"
    assert s["segment_idx"] == 0
    assert s["segment_text"] == "searchable segment text"
    assert "start" in s
    assert "end" in s


def test_get_search_response_shape_memo(client):
    _seed(client)
    resp = client.get("/api/search?q=searchable")
    items = resp.json()["items"]
    memo_items = [i for i in items if i["kind"] == "memo"]
    assert len(memo_items) == 1
    m = memo_items[0]
    assert m["job_id"] == "j1"
    assert m["memo_text"] == "searchable memo body"
    assert "memo_id" in m


def test_get_search_response_shape_job(client):
    _seed(client, title="Special title here")
    resp = client.get("/api/search?q=Special")
    items = resp.json()["items"]
    job_items = [i for i in items if i["kind"] == "job"]
    assert len(job_items) == 1
    j = job_items[0]
    assert j["job_id"] == "j1"
    assert j["job_title"] == "Special title here"


def test_get_search_limit_param(client):
    engine = client.app.state.engine
    job = Job(
        id="j1",
        source_url="https://e/j1",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title="T",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        for i in range(20):
            session.add(Segment(
                job_id="j1", idx=i,
                start=float(i), end=float(i) + 1,
                text=f"hello {i}",
            ))
        session.commit()

    resp = client.get("/api/search?q=hello&limit=5")
    items = resp.json()["items"]
    assert len(items) == 5
