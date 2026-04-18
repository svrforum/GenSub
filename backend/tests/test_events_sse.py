from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'sse.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return create_app()


def test_events_streams_progress_and_closes_on_terminal_state(tmp_path, monkeypatch):
    app = _setup(tmp_path, monkeypatch)
    engine = app.state.engine

    r = TestClient(app).post("/api/jobs", json={"url": "https://y/x", "model": "small"})
    job_id = r.json()["job_id"]

    with Session(engine) as s:
        job = s.get(Job, job_id)
        job.status = JobStatus.ready
        job.progress = 1.0
        job.stage_message = "준비됐어요"
        s.add(job)
        s.commit()

    with TestClient(app) as client, client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
        assert resp.status_code == 200
        got_progress = False
        got_done = False
        for line in resp.iter_lines():
            if line.startswith("event: progress"):
                got_progress = True
            if line.startswith("event: done"):
                got_done = True
                break
        assert got_progress
        assert got_done
