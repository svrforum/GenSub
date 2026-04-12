from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus
from app.services.segments import replace_all_segments
from app.services.subtitles import SegmentData


def _seed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'ms.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "js"
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
    replace_all_segments(
        app.state.engine,
        jid,
        [
            SegmentData(idx=0, start=0.0, end=1.0, text="hi"),
            SegmentData(idx=1, start=1.0, end=2.0, text="there"),
        ],
    )
    media = tmp_path / "media" / jid
    media.mkdir(parents=True, exist_ok=True)
    (media / "subtitles.srt").write_text("dummy-srt", encoding="utf-8")
    (media / "subtitles.vtt").write_text("WEBVTT\n", encoding="utf-8")
    return app, jid


def test_get_vtt(tmp_path, monkeypatch):
    app, jid = _seed(tmp_path, monkeypatch)
    r = TestClient(app).get(f"/api/jobs/{jid}/subtitles.vtt")
    assert r.status_code == 200
    assert "WEBVTT" in r.text


def test_get_srt(tmp_path, monkeypatch):
    app, jid = _seed(tmp_path, monkeypatch)
    r = TestClient(app).get(f"/api/jobs/{jid}/subtitles.srt")
    assert r.status_code == 200
    assert r.text == "dummy-srt"


def test_get_txt_generated_on_the_fly(tmp_path, monkeypatch):
    app, jid = _seed(tmp_path, monkeypatch)
    r = TestClient(app).get(f"/api/jobs/{jid}/transcript.txt")
    assert r.status_code == 200
    assert r.text == "hi\nthere\n"


def test_get_json_generated_on_the_fly(tmp_path, monkeypatch):
    app, jid = _seed(tmp_path, monkeypatch)
    r = TestClient(app).get(f"/api/jobs/{jid}/transcript.json")
    assert r.status_code == 200
    body = r.json()
    assert body["segments"][0]["text"] == "hi"
