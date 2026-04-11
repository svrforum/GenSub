from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app


def test_upload_creates_job_and_saves_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'u.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))

    client = TestClient(create_app())
    fake_video = BytesIO(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 256)
    r = client.post(
        "/api/jobs/upload",
        files={"file": ("test.mp4", fake_video, "video/mp4")},
        data={"model": "small"},
    )
    assert r.status_code == 201
    job_id = r.json()["job_id"]

    saved = tmp_path / "media" / job_id / "source.mp4"
    assert saved.exists()
    assert saved.stat().st_size > 0
