from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'mv.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return create_app(), tmp_path


def _seed_ready_job(app, tmp_path):
    jid = "jv"
    with Session(app.state.engine) as s:
        s.add(
            Job(
                id=jid,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()
    (tmp_path / "media" / jid).mkdir(parents=True, exist_ok=True)
    (tmp_path / "media" / jid / "source.mp4").write_bytes(b"0123456789" * 10)
    return jid


def test_video_full_response(tmp_path, monkeypatch):
    app, _ = _setup(tmp_path, monkeypatch)
    jid = _seed_ready_job(app, tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/jobs/{jid}/video")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("video/")
    assert len(r.content) == 100


def test_video_range_response(tmp_path, monkeypatch):
    app, _ = _setup(tmp_path, monkeypatch)
    jid = _seed_ready_job(app, tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/jobs/{jid}/video", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206
    assert r.content == b"0123456789"
    assert "bytes 10-19/100" in r.headers["content-range"]
    assert r.headers["content-length"] == "10"


def test_video_missing_404(tmp_path, monkeypatch):
    app, _ = _setup(tmp_path, monkeypatch)
    client = TestClient(app)
    r = client.get("/api/jobs/nope/video")
    assert r.status_code == 404
