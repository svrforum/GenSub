from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus


def _seed_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'mm.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jm"
    with Session(app.state.engine) as s:
        s.add(
            Job(
                id=jid,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                language="ko",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()
    media = tmp_path / "media" / jid
    media.mkdir(parents=True, exist_ok=True)
    (media / "source.mp4").write_bytes(b"video-bytes")
    (media / "subtitles.srt").write_text("srt", encoding="utf-8")
    return app, jid, media


def test_download_mkv_triggers_mux(tmp_path, monkeypatch):
    app, jid, media = _seed_ready(tmp_path, monkeypatch)
    client = TestClient(app)

    with patch("app.api.media.mux_video_with_subtitles") as mock_mux:

        def _fake(video, subtitle, output, language="und"):
            output.write_bytes(b"mkv-bytes")
            return output

        mock_mux.side_effect = _fake
        r = client.get(f"/api/jobs/{jid}/download/video+subs.mkv")
    assert r.status_code == 200
    assert r.content == b"mkv-bytes"
    assert "video+subs.mkv" in r.headers.get("content-disposition", "")


def test_download_burned_requires_done_state(tmp_path, monkeypatch):
    app, jid, media = _seed_ready(tmp_path, monkeypatch)
    client = TestClient(app)
    r = client.get(f"/api/jobs/{jid}/download/burned.mp4")
    assert r.status_code == 404  # still in ready state, burned.mp4 not written


def test_download_burned_returns_file_when_ready(tmp_path, monkeypatch):
    app, jid, media = _seed_ready(tmp_path, monkeypatch)
    (media / "burned.mp4").write_bytes(b"burned-bytes")
    with Session(app.state.engine) as s:
        job = s.get(Job, jid)
        job.status = JobStatus.done
        s.add(job)
        s.commit()
    r = TestClient(app).get(f"/api/jobs/{jid}/download/burned.mp4")
    assert r.status_code == 200
    assert r.content == b"burned-bytes"
