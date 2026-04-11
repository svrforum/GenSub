# Phase 6 — Segment Editing Endpoints

### Task 6.1: GET /segments + PATCH /segments/{idx}

**Files:**
- Create: `backend/app/api/segments.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_segments_endpoints.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_segments_endpoints.py`:

```python
from datetime import datetime, timedelta, timezone

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
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_segments_endpoints.py -v`

- [ ] **Step 3: segments 라우터 구현**

Write `backend/app/api/segments.py`:

```python
from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import SegmentPatchRequest, SearchReplaceRequest, SearchReplaceResponse
from app.services import jobs as jobs_service
from app.services.segments import (
    load_segments,
    load_segments_with_meta,
    search_and_replace,
    update_segment,
)
from app.services.subtitles import format_srt, format_vtt

router = APIRouter(prefix="/api/jobs", tags=["segments"])


def _rewrite_subtitle_files(settings, job_id: str, engine) -> None:
    segments = load_segments(engine, job_id)
    media_dir = settings.media_dir / job_id
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "subtitles.srt").write_text(format_srt(segments), encoding="utf-8")
    (media_dir / "subtitles.vtt").write_text(format_vtt(segments), encoding="utf-8")


@router.get("/{job_id}/segments")
def list_segments(job_id: str, request: Request) -> list[dict]:
    engine = request.app.state.engine
    if jobs_service.get_job(engine, job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return load_segments_with_meta(engine, job_id)


@router.patch("/{job_id}/segments/{idx}")
def patch_segment(
    job_id: str,
    idx: int,
    body: SegmentPatchRequest,
    request: Request,
) -> dict:
    engine = request.app.state.engine
    settings = request.app.state.settings
    if jobs_service.get_job(engine, job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")

    ok = update_segment(
        engine,
        job_id,
        idx,
        text=body.text,
        start=body.start,
        end=body.end,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="segment not found")
    _rewrite_subtitle_files(settings, job_id, engine)
    return {"ok": True}


@router.post("/{job_id}/search_replace")
def search_replace(
    job_id: str,
    body: SearchReplaceRequest,
    request: Request,
) -> SearchReplaceResponse:
    engine = request.app.state.engine
    settings = request.app.state.settings
    if jobs_service.get_job(engine, job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")

    changed = search_and_replace(
        engine, job_id, body.find, body.replace, body.case_sensitive
    )
    if changed:
        _rewrite_subtitle_files(settings, job_id, engine)
    return SearchReplaceResponse(changed_count=changed)
```

Modify `backend/app/main.py`: add `from app.api.segments import router as segments_router` and `app.include_router(segments_router)`.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_segments_endpoints.py -v`
Expected: 3 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/segments.py backend/app/main.py backend/tests/test_segments_endpoints.py
git commit -m "feat(backend): add segment listing, patching, search-replace endpoints"
```

---

### Task 6.2: 특정 세그먼트 재전사

**Files:**
- Create: `backend/app/services/regenerate.py`
- Modify: `backend/app/api/segments.py`
- Create: `backend/tests/test_regenerate.py`

- [ ] **Step 1: 실패 테스트 (전사기 모킹)**

Write `backend/tests/test_regenerate.py`:

```python
from datetime import datetime, timedelta, timezone
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
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
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

    with patch("app.services.regenerate.extract_audio") as mock_extract, patch(
        "app.services.regenerate._slice_audio"
    ) as mock_slice, patch(
        "app.services.regenerate.transcribe"
    ) as mock_tr:
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_regenerate.py -v`

- [ ] **Step 3: regenerate 서비스 + 엔드포인트 추가**

Write `backend/app/services/regenerate.py`:

```python
import subprocess
from pathlib import Path

from sqlalchemy.engine import Engine

from app.core.settings import Settings
from app.models.job import Job
from app.services.audio import extract_audio
from app.services.segments import load_segments, replace_all_segments
from app.services.subtitles import SegmentData
from app.services.transcriber import transcribe

PADDING_SEC = 2.0


def _slice_audio(source_wav: Path, dest_wav: Path, start: float, end: float) -> Path:
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_wav),
            "-ss",
            str(start),
            "-to",
            str(end),
            "-c",
            "copy",
            str(dest_wav),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"slice failed: {proc.stderr[:500]}")
    return dest_wav


def regenerate_segment(
    settings: Settings,
    engine: Engine,
    job: Job,
    idx: int,
) -> None:
    segments = load_segments(engine, job.id)
    target = next((s for s in segments if s.idx == idx), None)
    if target is None:
        raise RuntimeError("segment not found")

    media_dir = settings.media_dir / job.id
    audio_path = media_dir / "audio.wav"
    if not audio_path.exists():
        source = next(iter(media_dir.glob("source.*")), None)
        if source is None:
            raise RuntimeError("source missing")
        audio_path = extract_audio(source, audio_path)

    slice_start = max(0.0, target.start - PADDING_SEC)
    slice_end = target.end + PADDING_SEC
    slice_path = media_dir / f"slice-{idx}.wav"
    _slice_audio(audio_path, slice_path, slice_start, slice_end)

    result = transcribe(
        audio_path=slice_path,
        model_name=job.model_name,
        compute_type=settings.compute_type,
        model_cache_dir=settings.model_cache_dir,
        language=job.language,
        initial_prompt=job.initial_prompt,
    )
    slice_path.unlink(missing_ok=True)

    # 재전사 결과는 슬라이스 기준 상대 타임스탬프 → 절대값으로 보정
    adjusted = []
    for s in result.segments:
        adjusted.append(
            SegmentData(
                idx=0,
                start=s.start + slice_start,
                end=s.end + slice_start,
                text=s.text,
                avg_logprob=s.avg_logprob,
                no_speech_prob=s.no_speech_prob,
            )
        )

    # 원본 세그먼트 리스트에서 target을 제거하고 adjusted로 치환
    new_segments: list[SegmentData] = []
    for s in segments:
        if s.idx == idx:
            for i, a in enumerate(adjusted):
                new_segments.append(
                    SegmentData(
                        idx=0,
                        start=a.start,
                        end=a.end,
                        text=a.text,
                        avg_logprob=a.avg_logprob,
                        no_speech_prob=a.no_speech_prob,
                    )
                )
        else:
            new_segments.append(s)

    # idx 재번호 부여
    for i, s in enumerate(new_segments):
        s.idx = i

    replace_all_segments(engine, job.id, new_segments)
```

Append to `backend/app/api/segments.py`:

```python
from app.services import regenerate as regenerate_service


@router.post("/{job_id}/segments/{idx}/regenerate")
def regenerate_segment_endpoint(job_id: str, idx: int, request: Request) -> dict:
    engine = request.app.state.engine
    settings = request.app.state.settings
    job = jobs_service.get_job(engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    try:
        regenerate_service.regenerate_segment(settings, engine, job, idx)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _rewrite_subtitle_files(settings, job_id, engine)
    return {"ok": True}
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_regenerate.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/regenerate.py backend/app/api/segments.py backend/tests/test_regenerate.py
git commit -m "feat(backend): add per-segment re-transcription"
```

---

### Task 6.3: POST /api/jobs/{id}/burn

**Files:**
- Modify: `backend/app/api/jobs.py`
- Create: `backend/tests/test_burn_trigger.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_burn_trigger.py`:

```python
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus


def test_burn_transitions_ready_to_burning(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'bt.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jbt"
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

    r = TestClient(app).post(f"/api/jobs/{jid}/burn", json={})
    assert r.status_code == 200

    with Session(app.state.engine) as s:
        job = s.get(Job, jid)
        assert job.status == JobStatus.burning
        assert job.progress == 0.0
        assert job.stage_message == "자막을 영상에 입히고 있어요"


def test_burn_rejects_non_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'bt2.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    app = create_app()
    jid = "jbt2"
    with Session(app.state.engine) as s:
        s.add(
            Job(
                id=jid,
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.pending,
                progress=0.0,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        s.commit()
    r = TestClient(app).post(f"/api/jobs/{jid}/burn", json={})
    assert r.status_code == 409
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_burn_trigger.py -v`

- [ ] **Step 3: burn 엔드포인트 구현**

Append to `backend/app/api/jobs.py`:

```python
from datetime import datetime, timezone
from sqlmodel import Session

from app.models.job import Job, JobStatus
from pydantic import BaseModel


class BurnRequest(BaseModel):
    font: str = "Pretendard"
    size: int = 42
    outline: bool = True


@router.post("/{job_id}/burn")
def trigger_burn(job_id: str, body: BurnRequest, request: Request) -> dict:
    engine = request.app.state.engine
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if job.status not in (JobStatus.ready, JobStatus.done):
            raise HTTPException(
                status_code=409, detail=f"cannot burn from status {job.status.value}"
            )
        job.status = JobStatus.burning
        job.progress = 0.0
        job.stage_message = "자막을 영상에 입히고 있어요"
        job.updated_at = datetime.now(timezone.utc)
        job.initial_prompt = job.initial_prompt  # no-op, 편집 타이밍 확보
        s.add(job)
        s.commit()
    return {"ok": True}
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_burn_trigger.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/jobs.py backend/tests/test_burn_trigger.py
git commit -m "feat(backend): add POST /jobs/{id}/burn to trigger render"
```

---
