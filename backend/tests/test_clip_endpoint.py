from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus
from app.services.segments import replace_all_segments
from app.services.subtitles import SegmentData


def test_clip_endpoint_returns_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'cl.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jclip"
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
    media = tmp_path / "media" / jid
    media.mkdir(parents=True, exist_ok=True)
    (media / "source.mp4").write_bytes(b"video")
    replace_all_segments(
        app.state.engine,
        jid,
        [SegmentData(idx=0, start=0.0, end=5.0, text="hello")],
    )

    with patch("app.api.media.export_clip") as mock_clip:
        def _fake(video, output, start, end, segments=None, style=None):
            output.write_bytes(b"clipped")
            return output

        mock_clip.side_effect = _fake
        r = TestClient(app).post(
            f"/api/jobs/{jid}/clip",
            json={"start": 1.0, "end": 4.0},
        )
    assert r.status_code == 200
    assert r.content == b"clipped"
    assert "clip-1.0-4.0.mp4" in r.headers.get("content-disposition", "")
