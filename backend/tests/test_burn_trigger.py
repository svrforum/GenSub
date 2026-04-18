from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus


def test_burn_transitions_ready_to_burning(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'bt.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jbt"
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

    r = TestClient(app).post(f"/api/jobs/{jid}/burn", json={})
    assert r.status_code == 200

    with Session(app.state.engine) as s:
        job = s.get(Job, jid)
        assert job.status == JobStatus.burning
        assert job.progress == 0.0
        assert job.stage_message == "자막을 영상에 입히고 있어요"


def test_burn_rejects_non_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'bt2.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jbt2"
    with Session(app.state.engine) as s:
        s.add(
            Job(
                id=jid,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.pending,
                progress=0.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()
    r = TestClient(app).post(f"/api/jobs/{jid}/burn", json={})
    assert r.status_code == 409
