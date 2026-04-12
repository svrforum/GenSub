from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus
from app.services.segments import replace_all_segments
from app.services.subtitles import SegmentData


def _seed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'se.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jseg"
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
            SegmentData(idx=0, start=0.0, end=1.0, text="hi", avg_logprob=-0.2),
            SegmentData(idx=1, start=1.0, end=2.0, text="there", avg_logprob=-0.15),
        ],
    )
    (tmp_path / "media" / jid).mkdir(parents=True, exist_ok=True)
    return app, jid


def test_get_segments_returns_list(tmp_path, monkeypatch):
    app, jid = _seed(tmp_path, monkeypatch)
    r = TestClient(app).get(f"/api/jobs/{jid}/segments")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["text"] == "hi"
    assert data[0]["avg_logprob"] == -0.2


def test_patch_segment_text_persists(tmp_path, monkeypatch):
    app, jid = _seed(tmp_path, monkeypatch)
    client = TestClient(app)
    r = client.patch(f"/api/jobs/{jid}/segments/0", json={"text": "hello"})
    assert r.status_code == 200
    r2 = client.get(f"/api/jobs/{jid}/segments")
    assert r2.json()[0]["text"] == "hello"
    assert r2.json()[0]["edited"] is True


def test_patch_regenerates_subtitle_files(tmp_path, monkeypatch):
    app, jid = _seed(tmp_path, monkeypatch)
    TestClient(app).patch(f"/api/jobs/{jid}/segments/0", json={"text": "hello"})
    srt_path = tmp_path / "media" / jid / "subtitles.srt"
    assert srt_path.exists()
    content = srt_path.read_text(encoding="utf-8")
    assert "hello" in content
