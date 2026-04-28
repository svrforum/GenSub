from fastapi.testclient import TestClient

from app.main import create_app


def test_config_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'c.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("DEFAULT_MODEL", "small")

    client = TestClient(create_app())
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["default_model"] == "small"
    assert "tiny" in body["available_models"]
    assert "large-v3" in body["available_models"]
    assert body["max_video_minutes"] == 90
    assert "has_openai_fallback" not in body
    assert "job_ttl_hours" in body
    assert isinstance(body["job_ttl_hours"], int)
    assert body["job_ttl_hours"] > 0
