from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "jobs.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    return TestClient(app)


def _seed_memo(client) -> int:
    engine = client.app.state.engine
    job = Job(
        id="job1",
        source_url="https://e/1",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title="T",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    memo = Memo(
        job_id="job1", segment_idx=0,
        memo_text="note",
        segment_text_snapshot="s",
        segment_start=0, segment_end=1,
    )
    with Session(engine) as session:
        session.add(job)
        session.add(memo)
        session.commit()
        session.refresh(memo)
        return memo.id


def test_delete_memo_removes(client):
    mid = _seed_memo(client)
    resp = client.delete(f"/api/memos/{mid}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    resp2 = client.delete(f"/api/memos/{mid}")
    assert resp2.status_code == 404


def test_delete_missing_returns_404(client):
    resp = client.delete("/api/memos/99999")
    assert resp.status_code == 404


def test_patch_updates_text(client):
    mid = _seed_memo(client)
    resp = client.patch(f"/api/memos/{mid}", json={"memo_text": "updated"})
    assert resp.status_code == 200
    assert resp.json()["memo"]["memo_text"] == "updated"


def test_patch_rejects_over_500(client):
    mid = _seed_memo(client)
    resp = client.patch(f"/api/memos/{mid}", json={"memo_text": "x" * 501})
    assert resp.status_code == 422
