from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus
from app.services.segments import replace_all_segments
from app.services.subtitles import SegmentData
from app.services.transcriber import TranscribeResult


def test_regenerate_segment_replaces_text(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'rg.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jr"
    with Session(app.state.engine) as s:
        s.add(
            Job(
                id=jid,
                source_kind="upload",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                duration_sec=10.0,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        s.commit()
    replace_all_segments(
        app.state.engine,
        jid,
        [
            SegmentData(idx=0, start=0.0, end=3.0, text="wrong"),
            SegmentData(idx=1, start=3.0, end=6.0, text="ok"),
        ],
    )
    media = tmp_path / "media" / jid
    media.mkdir(parents=True, exist_ok=True)
    (media / "source.mp4").write_bytes(b"v")
    (media / "audio.wav").write_bytes(b"a")

    with (
        patch("app.services.regenerate.extract_audio") as mock_extract,
        patch("app.services.regenerate._slice_audio") as mock_slice,
        patch("app.services.regenerate.transcribe") as mock_tr,
    ):
        mock_extract.return_value = media / "audio.wav"
        mock_slice.return_value = media / "audio-slice.wav"
        mock_tr.return_value = TranscribeResult(
            segments=[SegmentData(idx=0, start=0.0, end=2.9, text="corrected")],
            language="en",
            duration=3.0,
        )
        r = TestClient(app).post(f"/api/jobs/{jid}/segments/0/regenerate")
    assert r.status_code == 200

    r2 = TestClient(app).get(f"/api/jobs/{jid}/segments")
    texts = [s["text"] for s in r2.json()]
    assert "corrected" in texts
    assert "ok" in texts
