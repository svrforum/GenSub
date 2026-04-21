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


def _seed_job(client, job_id="job1", title="Test"):
    engine = client.app.state.engine
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


def _seed_segment(client, job_id, idx, text):
    engine = client.app.state.engine
    with Session(engine) as session:
        session.add(Segment(
            job_id=job_id, idx=idx,
            start=float(idx), end=float(idx) + 1,
            text=text,
        ))
        session.commit()


def _seed_memo(client, job_id, idx, memo_text=""):
    engine = client.app.state.engine
    with Session(engine) as session:
        m = Memo(
            job_id=job_id, segment_idx=idx,
            memo_text=memo_text,
            segment_text_snapshot=f"snap {idx}",
            segment_start=float(idx), segment_end=float(idx) + 1,
            job_title_snapshot="T",
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        return m.id


def test_get_global_empty(client):
    resp = client.get("/api/memos")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_get_global_includes_liveness(client):
    _seed_job(client)
    _seed_segment(client, "job1", 0, "current text")
    _seed_memo(client, "job1", 0)

    resp = client.get("/api/memos")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["job_id"] == "job1"
    assert item["segment_text"] == "current text"
    assert item["job_alive"] is True


def test_get_global_orphan_shows_snapshot(client):
    _seed_memo(client, "orphan_job", 0)

    resp = client.get("/api/memos")
    [item] = resp.json()["items"]
    assert item["job_alive"] is False
    assert item["segment_text"] == "snap 0"


def test_get_global_limit(client):
    _seed_job(client)
    for i in range(5):
        _seed_segment(client, "job1", i, f"t{i}")
        _seed_memo(client, "job1", i)

    resp = client.get("/api/memos?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


def test_get_job_memos_returns_list(client):
    _seed_job(client)
    for i in (0, 2):
        _seed_segment(client, "job1", i, f"t{i}")
        _seed_memo(client, "job1", i)
    _seed_job(client, job_id="other")
    _seed_segment(client, "other", 0, "z")
    _seed_memo(client, "other", 0)

    resp = client.get("/api/jobs/job1/memos")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert {i["segment_idx"] for i in items} == {0, 2}
