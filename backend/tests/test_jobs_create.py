from fastapi.testclient import TestClient

from app.main import create_app


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return TestClient(create_app())


def test_create_job_with_url(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post(
        "/api/jobs",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "model": "small"},
    )
    assert r.status_code == 201
    body = r.json()
    assert "job_id" in body
    assert body["status"] == "pending"


def test_create_job_requires_url_for_url_kind(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/jobs", json={"model": "small"})
    assert r.status_code == 422
