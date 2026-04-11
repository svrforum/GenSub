# Phase 2 — Job Management API

### Task 2.1: 작업 생성 Pydantic 스키마

**Files:**
- Create: `backend/app/api/schemas.py`
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.api.schemas import JobCreateRequest


def test_job_create_requires_url_or_upload_kind():
    req = JobCreateRequest(url="https://youtu.be/abc", model="small")
    assert req.url == "https://youtu.be/abc"
    assert req.model == "small"
    assert req.language is None


def test_job_create_rejects_unknown_model():
    with pytest.raises(ValidationError):
        JobCreateRequest(url="https://youtu.be/abc", model="gigantic")


def test_job_create_accepts_initial_prompt():
    req = JobCreateRequest(
        url="https://youtu.be/abc", model="small", initial_prompt="transformer attention"
    )
    assert req.initial_prompt == "transformer attention"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`

- [ ] **Step 3: 스키마 구현**

Write `backend/app/api/schemas.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field

ModelName = Literal["tiny", "base", "small", "medium", "large-v3"]


class JobCreateRequest(BaseModel):
    url: str | None = None
    model: ModelName = "small"
    language: str | None = None
    initial_prompt: str | None = None


class JobResponse(BaseModel):
    id: str
    source_url: str | None
    source_kind: str
    title: str | None
    duration_sec: float | None
    language: str | None
    model_name: str
    status: str
    progress: float
    stage_message: str | None
    error_message: str | None
    created_at: str
    updated_at: str
    expires_at: str
    cancel_requested: bool


class SegmentResponse(BaseModel):
    idx: int
    start: float
    end: float
    text: str
    avg_logprob: float | None
    no_speech_prob: float | None
    edited: bool


class SegmentPatchRequest(BaseModel):
    text: str | None = None
    start: float | None = Field(default=None, ge=0.0)
    end: float | None = Field(default=None, ge=0.0)


class SearchReplaceRequest(BaseModel):
    find: str
    replace: str
    case_sensitive: bool = False


class SearchReplaceResponse(BaseModel):
    changed_count: int
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`
Expected: 3 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/schemas.py backend/tests/test_schemas.py
git commit -m "feat(backend): add Pydantic request/response schemas"
```

---

### Task 2.2: POST /api/jobs (URL 기반 작업 생성)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/jobs.py`
- Create: `backend/app/api/jobs.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_jobs_create.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_jobs_create.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return TestClient(create_app())


def test_create_job_with_url(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post(
        "/api/jobs",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "model": "small"},
    )
    assert r.status_code == 201
    body = r.json()
    assert "job_id" in body
    assert body["status"] == "pending"


def test_create_job_requires_url_for_url_kind(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/jobs", json={"model": "small"})
    assert r.status_code == 422
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_jobs_create.py -v`

- [ ] **Step 3: 서비스 레이어 + 라우터 구현**

Write `backend/app/services/__init__.py` (빈 파일):

```python
```

Write `backend/app/services/jobs.py`:

```python
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.settings import Settings
from app.models.job import Job, JobStatus, SourceKind


def create_job_from_url(
    engine: Engine,
    settings: Settings,
    url: str,
    model: str,
    language: str | None,
    initial_prompt: str | None,
) -> Job:
    now = datetime.now(timezone.utc)
    job = Job(
        id=uuid4().hex,
        source_url=url,
        source_kind=SourceKind.url.value,
        model_name=model,
        language=language,
        initial_prompt=initial_prompt,
        status=JobStatus.pending,
        progress=0.0,
        stage_message="준비하고 있어요",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=settings.job_ttl_hours),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
        s.refresh(job)
    return job
```

Write `backend/app/api/jobs.py`:

```python
from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas import JobCreateRequest
from app.services import jobs as jobs_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job(body: JobCreateRequest, request: Request) -> dict:
    if not body.url:
        raise HTTPException(status_code=422, detail="url is required for URL-based jobs")

    engine = request.app.state.engine
    settings = request.app.state.settings
    job = jobs_service.create_job_from_url(
        engine=engine,
        settings=settings,
        url=body.url,
        model=body.model,
        language=body.language,
        initial_prompt=body.initial_prompt,
    )
    return {"job_id": job.id, "status": job.status.value}
```

Modify `backend/app/main.py`: add `from app.api.jobs import router as jobs_router` and `app.include_router(jobs_router)` after config_router.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_jobs_create.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/ backend/app/api/jobs.py backend/app/main.py backend/tests/test_jobs_create.py
git commit -m "feat(backend): add POST /api/jobs for URL-based job creation"
```

---

### Task 2.3: POST /api/jobs/upload (로컬 파일 업로드)

**Files:**
- Modify: `backend/app/services/jobs.py`
- Modify: `backend/app/api/jobs.py`
- Create: `backend/tests/test_jobs_upload.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_jobs_upload.py`:

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_jobs_upload.py -v`

- [ ] **Step 3: 서비스 함수 추가 + 라우터 확장**

Append to `backend/app/services/jobs.py`:

```python
from pathlib import Path


def create_job_from_upload(
    engine: Engine,
    settings: Settings,
    filename: str,
    model: str,
    language: str | None,
    initial_prompt: str | None,
) -> tuple[Job, Path]:
    now = datetime.now(timezone.utc)
    job_id = uuid4().hex
    suffix = Path(filename).suffix or ".mp4"
    job_dir = settings.media_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / f"source{suffix}"

    job = Job(
        id=job_id,
        source_url=None,
        source_kind=SourceKind.upload.value,
        title=filename,
        model_name=model,
        language=language,
        initial_prompt=initial_prompt,
        status=JobStatus.pending,
        progress=0.0,
        stage_message="준비하고 있어요",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=settings.job_ttl_hours),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
        s.refresh(job)
    return job, dest
```

Append to `backend/app/api/jobs.py`:

```python
from fastapi import File, Form, UploadFile


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_job(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form("small"),
    language: str | None = Form(None),
    initial_prompt: str | None = Form(None),
) -> dict:
    settings = request.app.state.settings
    engine = request.app.state.engine

    max_bytes = settings.max_upload_mb * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"file exceeds {settings.max_upload_mb} MB")

    job, dest = jobs_service.create_job_from_upload(
        engine=engine,
        settings=settings,
        filename=file.filename or "upload.mp4",
        model=model,
        language=language,
        initial_prompt=initial_prompt,
    )
    dest.write_bytes(contents)
    return {"job_id": job.id, "status": job.status.value}
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_jobs_upload.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/jobs.py backend/app/api/jobs.py backend/tests/test_jobs_upload.py
git commit -m "feat(backend): add POST /api/jobs/upload for local files"
```

---

### Task 2.4: GET /api/jobs/{id}

**Files:**
- Modify: `backend/app/services/jobs.py`
- Modify: `backend/app/api/jobs.py`
- Create: `backend/tests/test_jobs_read.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_jobs_read.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_get_job_by_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'r.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    client = TestClient(create_app())

    r = client.post("/api/jobs", json={"url": "https://youtu.be/x", "model": "small"})
    job_id = r.json()["job_id"]

    r2 = client.get(f"/api/jobs/{job_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["id"] == job_id
    assert body["status"] == "pending"
    assert body["source_kind"] == "url"
    assert body["progress"] == 0.0


def test_get_unknown_job_404(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'r2.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    client = TestClient(create_app())

    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_jobs_read.py -v`

- [ ] **Step 3: 서비스 함수 추가 + 라우터 추가**

Append to `backend/app/services/jobs.py`:

```python
def get_job(engine: Engine, job_id: str) -> Job | None:
    with Session(engine) as s:
        return s.get(Job, job_id)


def job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "source_url": job.source_url,
        "source_kind": job.source_kind,
        "title": job.title,
        "duration_sec": job.duration_sec,
        "language": job.language,
        "model_name": job.model_name,
        "status": job.status.value if hasattr(job.status, "value") else job.status,
        "progress": job.progress,
        "stage_message": job.stage_message,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "expires_at": job.expires_at.isoformat(),
        "cancel_requested": job.cancel_requested,
    }
```

Append to `backend/app/api/jobs.py`:

```python
@router.get("/{job_id}")
def get_job(job_id: str, request: Request) -> dict:
    job = jobs_service.get_job(request.app.state.engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return jobs_service.job_to_dict(job)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_jobs_read.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/jobs.py backend/app/api/jobs.py backend/tests/test_jobs_read.py
git commit -m "feat(backend): add GET /api/jobs/{id}"
```

---

### Task 2.5: POST /api/jobs/{id}/cancel + DELETE /api/jobs/{id}

**Files:**
- Modify: `backend/app/services/jobs.py`
- Modify: `backend/app/api/jobs.py`
- Create: `backend/tests/test_jobs_lifecycle.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_jobs_lifecycle.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'lc.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return TestClient(create_app())


def test_cancel_sets_cancel_requested(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    r = client.post("/api/jobs", json={"url": "https://y/x", "model": "small"})
    job_id = r.json()["job_id"]

    r2 = client.post(f"/api/jobs/{job_id}/cancel")
    assert r2.status_code == 200
    assert r2.json() == {"ok": True}

    r3 = client.get(f"/api/jobs/{job_id}")
    assert r3.json()["cancel_requested"] is True


def test_delete_removes_job_and_directory(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    r = client.post("/api/jobs", json={"url": "https://y/x", "model": "small"})
    job_id = r.json()["job_id"]

    job_dir = tmp_path / "media" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "dummy.txt").write_text("x")

    r2 = client.delete(f"/api/jobs/{job_id}")
    assert r2.status_code == 200

    r3 = client.get(f"/api/jobs/{job_id}")
    assert r3.status_code == 404
    assert not job_dir.exists()
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_jobs_lifecycle.py -v`

- [ ] **Step 3: 서비스 + 라우터 추가**

Append to `backend/app/services/jobs.py`:

```python
import shutil


def request_cancel(engine: Engine, job_id: str) -> bool:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return False
        job.cancel_requested = True
        job.updated_at = datetime.now(timezone.utc)
        s.add(job)
        s.commit()
        return True


def delete_job(engine: Engine, settings: Settings, job_id: str) -> bool:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            return False
        s.delete(job)
        s.commit()
    job_dir = settings.media_dir / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    return True
```

Append to `backend/app/api/jobs.py`:

```python
@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, request: Request) -> dict:
    ok = jobs_service.request_cancel(request.app.state.engine, job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True}


@router.delete("/{job_id}")
def delete_job(job_id: str, request: Request) -> dict:
    ok = jobs_service.delete_job(
        request.app.state.engine, request.app.state.settings, job_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True}
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_jobs_lifecycle.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/jobs.py backend/app/api/jobs.py backend/tests/test_jobs_lifecycle.py
git commit -m "feat(backend): add cancel and delete endpoints"
```

---

### Task 2.6: SSE /api/jobs/{id}/events

**Files:**
- Create: `backend/app/api/events.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_events_sse.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_events_sse.py`:

```python
import json

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'sse.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return create_app()


def test_events_streams_progress_and_closes_on_terminal_state(tmp_path, monkeypatch):
    app = _setup(tmp_path, monkeypatch)
    engine = app.state.engine

    r = TestClient(app).post("/api/jobs", json={"url": "https://y/x", "model": "small"})
    job_id = r.json()["job_id"]

    with Session(engine) as s:
        job = s.get(Job, job_id)
        job.status = JobStatus.ready
        job.progress = 1.0
        job.stage_message = "준비됐어요"
        s.add(job)
        s.commit()

    with TestClient(app) as client:
        with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
            assert resp.status_code == 200
            got_progress = False
            got_done = False
            for line in resp.iter_lines():
                if line.startswith("event: progress"):
                    got_progress = True
                if line.startswith("event: done"):
                    got_done = True
                    break
            assert got_progress
            assert got_done
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_events_sse.py -v`

- [ ] **Step 3: events 라우터 구현**

Write `backend/app/api/events.py`:

```python
import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.services import jobs as jobs_service

router = APIRouter(prefix="/api/jobs", tags=["events"])

TERMINAL_STATES = {"ready", "done", "failed"}
POLL_INTERVAL_SEC = 0.5


@router.get("/{job_id}/events")
async def events(job_id: str, request: Request):
    engine = request.app.state.engine
    job = jobs_service.get_job(engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_gen():
        last_snapshot = None
        while True:
            if await request.is_disconnected():
                return
            current = jobs_service.get_job(engine, job_id)
            if current is None:
                yield {"event": "error", "data": json.dumps({"message": "job disappeared"})}
                return
            snapshot = (
                current.status.value if hasattr(current.status, "value") else current.status,
                current.progress,
                current.stage_message,
                current.error_message,
            )
            if snapshot != last_snapshot:
                last_snapshot = snapshot
                status_val, progress, stage_message, error_message = snapshot
                if status_val == "failed":
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": error_message or "unknown error"}),
                    }
                    return
                yield {
                    "event": "progress",
                    "data": json.dumps(
                        {
                            "status": status_val,
                            "progress": progress,
                            "stage_message": stage_message,
                        }
                    ),
                }
                if status_val in TERMINAL_STATES:
                    yield {"event": "done", "data": json.dumps({"status": status_val})}
                    return
            await asyncio.sleep(POLL_INTERVAL_SEC)

    return EventSourceResponse(event_gen())
```

Modify `backend/app/main.py`: add `from app.api.events import router as events_router` and `app.include_router(events_router)`.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_events_sse.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/events.py backend/app/main.py backend/tests/test_events_sse.py
git commit -m "feat(backend): add SSE progress stream at /api/jobs/{id}/events"
```

---

### Task 2.7: 시작 시 좀비 정리 + TTL 루프

**Files:**
- Create: `backend/app/services/cleanup.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_cleanup.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_cleanup.py`:

```python
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.cleanup import purge_expired_jobs, sweep_zombie_jobs


def _make_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    return Settings(database_url=f"sqlite:///{tmp_path/'c.db'}")


def test_sweep_zombie_jobs_marks_in_progress_as_failed(tmp_path, monkeypatch):
    settings = _make_settings(tmp_path, monkeypatch)
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    now = datetime.now(timezone.utc)
    with Session(engine) as s:
        for i, st in enumerate(
            [JobStatus.downloading, JobStatus.transcribing, JobStatus.burning, JobStatus.ready]
        ):
            s.add(
                Job(
                    id=f"j{i}",
                    source_kind="url",
                    source_url="https://y/x",
                    model_name="small",
                    status=st,
                    progress=0.5,
                    expires_at=now + timedelta(hours=1),
                )
            )
        s.commit()

    n = sweep_zombie_jobs(engine)
    assert n == 3

    with Session(engine) as s:
        assert s.get(Job, "j0").status == JobStatus.failed
        assert s.get(Job, "j3").status == JobStatus.ready


def test_purge_expired_jobs_deletes_db_and_dir(tmp_path, monkeypatch):
    settings = _make_settings(tmp_path, monkeypatch)
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    now = datetime.now(timezone.utc)
    with Session(engine) as s:
        s.add(
            Job(
                id="old",
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                expires_at=now - timedelta(hours=1),
            )
        )
        s.add(
            Job(
                id="new",
                source_kind="url",
                source_url="https://y/x",
                model_name="small",
                status=JobStatus.ready,
                progress=1.0,
                expires_at=now + timedelta(hours=1),
            )
        )
        s.commit()

    job_dir = settings.media_dir / "old"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "a.txt").write_text("x")

    n = purge_expired_jobs(engine, settings)
    assert n == 1
    assert not job_dir.exists()

    with Session(engine) as s:
        assert s.get(Job, "old") is None
        assert s.get(Job, "new") is not None
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_cleanup.py -v`

- [ ] **Step 3: cleanup 서비스 구현**

Write `backend/app/services/cleanup.py`:

```python
import shutil
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.settings import Settings
from app.models.job import Job, JobStatus

ACTIVE_STATES = {JobStatus.downloading, JobStatus.transcribing, JobStatus.burning}


def sweep_zombie_jobs(engine: Engine) -> int:
    now = datetime.now(timezone.utc)
    count = 0
    with Session(engine) as s:
        rows = s.exec(select(Job).where(Job.status.in_([st.value for st in ACTIVE_STATES]))).all()
        for job in rows:
            job.status = JobStatus.failed
            job.error_message = "컨테이너 재시작으로 인해 중단되었어요"
            job.updated_at = now
            s.add(job)
            count += 1
        s.commit()
    return count


def purge_expired_jobs(engine: Engine, settings: Settings) -> int:
    now = datetime.now(timezone.utc)
    count = 0
    with Session(engine) as s:
        rows = s.exec(select(Job).where(Job.expires_at < now)).all()
        for job in rows:
            job_dir = settings.media_dir / job.id
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)
            s.delete(job)
            count += 1
        s.commit()
    return count
```

Modify `backend/app/main.py`: 앱 생성 직후 `sweep_zombie_jobs(engine)`를 호출하고, 백그라운드 정리 태스크를 `@app.on_event("startup")`로 스케줄.

Replace the `create_app` body so it ends like this (keep earlier imports and middleware config):

```python
from contextlib import asynccontextmanager
import asyncio

from app.services.cleanup import purge_expired_jobs, sweep_zombie_jobs


async def _cleanup_loop(app: FastAPI):
    while True:
        await asyncio.sleep(3600)
        try:
            purge_expired_jobs(app.state.engine, app.state.settings)
        except Exception:
            pass


@asynccontextmanager
async def _lifespan(app: FastAPI):
    sweep_zombie_jobs(app.state.engine)
    task = asyncio.create_task(_cleanup_loop(app))
    try:
        yield
    finally:
        task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GenSub", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_allow_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    app.state.engine = engine
    app.state.settings = settings

    app.include_router(health_router)
    app.include_router(config_router)
    app.include_router(jobs_router)
    app.include_router(events_router)
    return app


app = create_app()
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/ -v`
Expected: 전체 그린.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/cleanup.py backend/app/main.py backend/tests/test_cleanup.py
git commit -m "feat(backend): sweep zombies on startup and periodic TTL purge"
```

---

