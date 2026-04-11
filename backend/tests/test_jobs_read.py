from fastapi.testclient import TestClient

from app.main import create_app


def test_get_job_by_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'r.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    client = TestClient(create_app())

    r = client.post("/api/jobs", json={"url": "https://youtu.be/x", "model": "small"})
    job_id = r.json()["job_id"]

    r2 = client.get(f"/api/jobs/{job_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["id"] == job_id
    assert body["status"] == "pending"
    assert body["source_kind"] == "url"
    assert body["progress"] == 0.0


def test_get_unknown_job_404(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'r2.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    client = TestClient(create_app())

    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404
