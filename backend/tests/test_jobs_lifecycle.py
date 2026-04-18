from fastapi.testclient import TestClient

from app.main import create_app


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'lc.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return TestClient(create_app())


def test_cancel_sets_cancel_requested(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    r = client.post("/api/jobs", json={"url": "https://y/x", "model": "small"})
    job_id = r.json()["job_id"]

    r2 = client.post(f"/api/jobs/{job_id}/cancel")
    assert r2.status_code == 200
    assert r2.json() == {"ok": True}

    r3 = client.get(f"/api/jobs/{job_id}")
    assert r3.json()["cancel_requested"] is True


def test_delete_removes_job_and_directory(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    r = client.post("/api/jobs", json={"url": "https://y/x", "model": "small"})
    job_id = r.json()["job_id"]

    job_dir = tmp_path / "media" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "dummy.txt").write_text("x")

    r2 = client.delete(f"/api/jobs/{job_id}")
    assert r2.status_code == 200

    r3 = client.get(f"/api/jobs/{job_id}")
    assert r3.status_code == 404
    assert not job_dir.exists()
