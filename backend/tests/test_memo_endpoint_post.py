from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus, SourceKind
from app.models.segment import Segment


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "jobs.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    from app.core.settings import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None

    app = create_app()
    return TestClient(app)


def _seed(client: TestClient):
    engine = client.app.state.engine
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


def test_post_creates_memo_201(client):
    _seed(client)
    resp = client.post("/api/jobs/job1/segments/3/memo")
    assert resp.status_code == 201
    body = resp.json()
    assert body["ok"] is True
    assert body["action"] == "created"
    assert body["memo"]["memo_text"] == ""
    assert body["memo"]["segment_text_snapshot"] == "Hello world"
    assert body["memo"]["job_id"] == "job1"


def test_post_toggles_off_when_empty_200(client):
    _seed(client)
    client.post("/api/jobs/job1/segments/3/memo")
    resp = client.post("/api/jobs/job1/segments/3/memo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "deleted"


def test_post_409_when_memo_has_text(client):
    _seed(client)
    first = client.post("/api/jobs/job1/segments/3/memo").json()
    client.patch(f"/api/memos/{first['memo']['id']}", json={"memo_text": "keep me"})

    resp = client.post("/api/jobs/job1/segments/3/memo")
    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["reason"] == "memo_has_text"
    assert body["detail"]["memo_id"] == first["memo"]["id"]


def test_post_404_when_segment_missing(client):
    _seed(client)
    resp = client.post("/api/jobs/job1/segments/999/memo")
    assert resp.status_code == 404


def test_post_404_when_job_missing(client):
    resp = client.post("/api/jobs/nonexistent/segments/0/memo")
    assert resp.status_code == 404


def test_post_auto_pins_job(client):
    _seed(client)
    client.post("/api/jobs/job1/segments/3/memo")
    engine = client.app.state.engine
    with Session(engine) as session:
        job = session.get(Job, "job1")
        assert job.pinned is True
