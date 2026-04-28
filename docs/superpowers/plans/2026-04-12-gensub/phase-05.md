# Phase 5 — Media Serving Endpoints

### Task 5.1: HTTP Range 지원 비디오 스트리밍

**Files:**
- Create: `backend/app/api/media.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_media_video.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_media_video.py`:

```python
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus


def _setup(tmp_path, monkeypatch):
 monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'mv.db'}")
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 return create_app(), tmp_path


def _seed_ready_job(app, tmp_path):
 jid = "jv"
 with Session(app.state.engine) as s:
 s.add(
 Job(
 id=jid,
 source_kind="url",
 source_url="https://y/x",
 model_name="small",
 status=JobStatus.ready,
 progress=1.0,
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
 )
 )
 s.commit()
 (tmp_path / "media" / jid).mkdir(parents=True, exist_ok=True)
 (tmp_path / "media" / jid / "source.mp4").write_bytes(b"0123456789" * 10)
 return jid


def test_video_full_response(tmp_path, monkeypatch):
 app, _ = _setup(tmp_path, monkeypatch)
 jid = _seed_ready_job(app, tmp_path)
 client = TestClient(app)
 r = client.get(f"/api/jobs/{jid}/video")
 assert r.status_code == 200
 assert r.headers["content-type"].startswith("video/")
 assert len(r.content) == 100


def test_video_range_response(tmp_path, monkeypatch):
 app, _ = _setup(tmp_path, monkeypatch)
 jid = _seed_ready_job(app, tmp_path)
 client = TestClient(app)
 r = client.get(f"/api/jobs/{jid}/video", headers={"Range": "bytes=10-19"})
 assert r.status_code == 206
 assert r.content == b"0123456789"
 assert "bytes 10-19/100" in r.headers["content-range"]
 assert r.headers["content-length"] == "10"


def test_video_missing_404(tmp_path, monkeypatch):
 app, _ = _setup(tmp_path, monkeypatch)
 client = TestClient(app)
 r = client.get("/api/jobs/nope/video")
 assert r.status_code == 404
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_media_video.py -v`

- [ ] **Step 3: 미디어 라우터 구현**

Write `backend/app/api/media.py`:

```python
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from app.services import jobs as jobs_service

router = APIRouter(prefix="/api/jobs", tags=["media"])

CHUNK_SIZE = 1024 * 512 # 512KB


def _resolve_source(settings, job_id: str) -> Path:
 media_dir = settings.media_dir / job_id
 for candidate in sorted(media_dir.glob("source.*")):
 return candidate
 raise HTTPException(status_code=404, detail="source file not found")


def _parse_range(header: str, file_size: int) -> tuple[int, int]:
 unit, _, spec = header.partition("=")
 if unit.strip() != "bytes":
 raise ValueError("unsupported range unit")
 start_s, _, end_s = spec.partition("-")
 start = int(start_s) if start_s else 0
 end = int(end_s) if end_s else file_size - 1
 if start < 0 or end >= file_size or start > end:
 raise ValueError("range out of bounds")
 return start, end


def _file_iter(path: Path, start: int, end: int):
 remaining = end - start + 1
 with path.open("rb") as f:
 f.seek(start)
 while remaining > 0:
 chunk = f.read(min(CHUNK_SIZE, remaining))
 if not chunk:
 break
 remaining -= len(chunk)
 yield chunk


@router.get("/{job_id}/video")
def get_video(job_id: str, request: Request) -> Response:
 engine = request.app.state.engine
 settings = request.app.state.settings

 job = jobs_service.get_job(engine, job_id)
 if job is None:
 raise HTTPException(status_code=404, detail="job not found")

 src = _resolve_source(settings, job_id)
 file_size = src.stat().st_size
 content_type = mimetypes.guess_type(str(src))[0] or "video/mp4"
 range_header = request.headers.get("range")

 if range_header is None:
 return StreamingResponse(
 _file_iter(src, 0, file_size - 1),
 media_type=content_type,
 headers={
 "Content-Length": str(file_size),
 "Accept-Ranges": "bytes",
 },
 )

 try:
 start, end = _parse_range(range_header, file_size)
 except ValueError:
 raise HTTPException(status_code=416, detail="range not satisfiable")

 length = end - start + 1
 return StreamingResponse(
 _file_iter(src, start, end),
 status_code=206,
 media_type=content_type,
 headers={
 "Content-Range": f"bytes {start}-{end}/{file_size}",
 "Content-Length": str(length),
 "Accept-Ranges": "bytes",
 },
 )
```

Modify `backend/app/main.py`: add `from app.api.media import router as media_router` and `app.include_router(media_router)`.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_media_video.py -v`
Expected: 3 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/media.py backend/app/main.py backend/tests/test_media_video.py
git commit -m "feat(backend): add GET /video with HTTP Range support"
```

---

### Task 5.2: 자막 파일 다운로드 (VTT / SRT / TXT / JSON)

**Files:**
- Modify: `backend/app/api/media.py`
- Create: `backend/tests/test_media_subtitles.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_media_subtitles.py`:

```python
from datetime import datetime, timedelta, timezone

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
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_media_subtitles.py -v`

- [ ] **Step 3: 라우터 확장**

Append to `backend/app/api/media.py`:

```python
import json

from fastapi.responses import FileResponse, PlainTextResponse

from app.services.segments import load_segments
from app.services.subtitles import format_json, format_txt


@router.get("/{job_id}/subtitles.vtt")
def get_vtt(job_id: str, request: Request):
 settings = request.app.state.settings
 path = settings.media_dir / job_id / "subtitles.vtt"
 if not path.exists():
 raise HTTPException(status_code=404, detail="subtitles not ready")
 return FileResponse(path, media_type="text/vtt; charset=utf-8")


@router.get("/{job_id}/subtitles.srt")
def get_srt(job_id: str, request: Request):
 settings = request.app.state.settings
 path = settings.media_dir / job_id / "subtitles.srt"
 if not path.exists():
 raise HTTPException(status_code=404, detail="subtitles not ready")
 return FileResponse(
 path,
 media_type="application/x-subrip",
 filename="subtitles.srt",
 )


@router.get("/{job_id}/transcript.txt")
def get_txt(job_id: str, request: Request):
 engine = request.app.state.engine
 segments = load_segments(engine, job_id)
 return PlainTextResponse(format_txt(segments), media_type="text/plain; charset=utf-8")


@router.get("/{job_id}/transcript.json")
def get_json(job_id: str, request: Request):
 engine = request.app.state.engine
 segments = load_segments(engine, job_id)
 return Response(
 content=format_json(segments),
 media_type="application/json; charset=utf-8",
 )
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_media_subtitles.py -v`
Expected: 4 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/media.py backend/tests/test_media_subtitles.py
git commit -m "feat(backend): add subtitle file download endpoints"
```

---

### Task 5.3: MKV 먹스 다운로드 + Burned mp4 다운로드

**Files:**
- Modify: `backend/app/api/media.py`
- Create: `backend/tests/test_media_mux.py`

- [ ] **Step 1: 실패 테스트 (mkvmerge 모킹)**

Write `backend/tests/test_media_mux.py`:

```python
from datetime import datetime, timedelta, timezone
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
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
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
 assert r.status_code == 404 # 아직 burning 안 됨


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
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_media_mux.py -v`

- [ ] **Step 3: mkv 및 burned 다운로드 엔드포인트 추가**

Append to `backend/app/api/media.py`:

```python
from app.services.muxer import mux_video_with_subtitles


@router.get("/{job_id}/download/video+subs.mkv")
def download_mkv(job_id: str, request: Request):
 engine = request.app.state.engine
 settings = request.app.state.settings

 job = jobs_service.get_job(engine, job_id)
 if job is None:
 raise HTTPException(status_code=404, detail="job not found")

 media_dir = settings.media_dir / job_id
 srt = media_dir / "subtitles.srt"
 if not srt.exists():
 raise HTTPException(status_code=404, detail="subtitles not ready")
 src = _resolve_source(settings, job_id)
 output = media_dir / "video+subs.mkv"

 mux_video_with_subtitles(
 video=src,
 subtitle=srt,
 output=output,
 language=job.language or "und",
 )
 return FileResponse(
 output,
 media_type="video/x-matroska",
 filename="video+subs.mkv",
 )


@router.get("/{job_id}/download/burned.mp4")
def download_burned(job_id: str, request: Request):
 settings = request.app.state.settings
 path = settings.media_dir / job_id / "burned.mp4"
 if not path.exists():
 raise HTTPException(status_code=404, detail="burned file not ready")
 return FileResponse(
 path,
 media_type="video/mp4",
 filename="burned.mp4",
 )
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_media_mux.py -v`
Expected: 3 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/media.py backend/tests/test_media_mux.py
git commit -m "feat(backend): add mkv mux and burned mp4 download endpoints"
```

---

