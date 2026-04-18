from fastapi.testclient import TestClient

from app.main import create_app


def test_root_serves_index_html(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'st.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>stub</html>")
    monkeypatch.setenv("STATIC_DIR", str(static_dir))

    client = TestClient(create_app())
    r = client.get("/")
    assert r.status_code == 200
    assert "stub" in r.text


def test_api_routes_still_work_with_static_mount(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'st2.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html></html>")
    monkeypatch.setenv("STATIC_DIR", str(static_dir))

    client = TestClient(create_app())
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
