# Phase 1 — Backend Foundation (설정, DB, 모델)

### Task 1.1: Settings 모듈 (pydantic-settings)

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/settings.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_settings.py`

- [ ] **Step 1: 실패하는 테스트 먼저 작성**

Write `backend/tests/test_settings.py`:

```python
from app.core.settings import Settings


def test_settings_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    s = Settings()
    assert s.gensub_role in ("api", "worker")
    assert s.job_ttl_hours == 24
    assert s.max_video_minutes == 90
    assert s.default_model == "small"
    assert s.compute_type == "int8"
    assert s.worker_concurrency == 1


def test_settings_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_TTL_HOURS", "48")
    monkeypatch.setenv("DEFAULT_MODEL", "medium")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    s = Settings()
    assert s.job_ttl_hours == 48
    assert s.default_model == "medium"
```

- [ ] **Step 2: 테스트가 ImportError로 실패하는지 확인**

Run: `cd backend && uv run pytest tests/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: app.core.settings`.

- [ ] **Step 3: Settings 모듈 구현**

Write `backend/app/__init__.py` (빈 파일):

```python
```

Write `backend/app/core/__init__.py` (빈 파일):

```python
```

Write `backend/app/core/settings.py`:

```python
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gensub_role: Literal["api", "worker"] = "api"
    database_url: str = "sqlite:////data/db/jobs.db"
    media_dir: Path = Path("/data/media")
    model_cache_dir: Path = Path("/data/models")

    job_ttl_hours: int = Field(default=24, ge=1)
    max_video_minutes: int = Field(default=90, ge=1)
    default_model: str = "small"
    compute_type: Literal["int8", "int8_float16", "float16", "float32"] = "int8"
    worker_concurrency: int = Field(default=1, ge=1, le=8)

    openai_api_key: str = ""
    cors_allow_origin: str = "*"

    max_upload_mb: int = Field(default=2048, ge=1)


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_settings.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/__init__.py backend/app/core/ backend/tests/
git commit -m "feat(backend): add settings module with pydantic-settings"
```

---

### Task 1.2: SQLModel — Job 테이블

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/job.py`
- Create: `backend/tests/test_models_job.py`

- [ ] **Step 1: 실패 테스트 먼저**

Write `backend/tests/test_models_job.py`:

```python
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine

from app.models.job import Job, JobStatus


def test_job_creation_and_persistence():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        job = Job(
            id="abc123",
            source_url="https://youtube.com/watch?v=xyz",
            source_kind="url",
            model_name="small",
            status=JobStatus.pending,
            progress=0.0,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        session.add(job)
        session.commit()

    with Session(engine) as session:
        fetched = session.get(Job, "abc123")
        assert fetched is not None
        assert fetched.status == JobStatus.pending
        assert fetched.source_kind == "url"
        assert fetched.cancel_requested is False


def test_job_status_values():
    assert JobStatus.pending.value == "pending"
    assert JobStatus.downloading.value == "downloading"
    assert JobStatus.transcribing.value == "transcribing"
    assert JobStatus.ready.value == "ready"
    assert JobStatus.burning.value == "burning"
    assert JobStatus.done.value == "done"
    assert JobStatus.failed.value == "failed"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_models_job.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Job 모델 구현**

Write `backend/app/models/__init__.py` (빈 파일):

```python
```

Write `backend/app/models/job.py`:

```python
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    pending = "pending"
    downloading = "downloading"
    transcribing = "transcribing"
    ready = "ready"
    burning = "burning"
    done = "done"
    failed = "failed"


class SourceKind(str, Enum):
    url = "url"
    upload = "upload"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(SQLModel, table=True):
    __tablename__ = "job"

    id: str = Field(primary_key=True)
    source_url: str | None = None
    source_kind: str
    title: str | None = None
    duration_sec: float | None = None
    language: str | None = None
    model_name: str
    initial_prompt: str | None = None
    status: JobStatus = JobStatus.pending
    progress: float = 0.0
    stage_message: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime
    cancel_requested: bool = False
```

- [ ] **Step 4: 테스트 통과**

Run: `cd backend && uv run pytest tests/test_models_job.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/models/ backend/tests/test_models_job.py
git commit -m "feat(backend): add Job model with status enum"
```

---

### Task 1.3: Segment 모델

**Files:**
- Create: `backend/app/models/segment.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models_segment.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_models_segment.py`:

```python
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine, select

from app.models.job import Job, JobStatus
from app.models.segment import Segment


def test_segment_belongs_to_job():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        job = Job(
            id="j1",
            source_kind="upload",
            model_name="small",
            status=JobStatus.ready,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        s.add(job)
        s.add(Segment(job_id="j1", idx=0, start=0.0, end=3.5, text="안녕하세요", avg_logprob=-0.2))
        s.add(Segment(job_id="j1", idx=1, start=3.5, end=7.0, text="반갑습니다", avg_logprob=-0.1))
        s.commit()

        rows = s.exec(
            select(Segment).where(Segment.job_id == "j1").order_by(Segment.idx)
        ).all()
        assert len(rows) == 2
        assert rows[0].text == "안녕하세요"
        assert rows[1].start == 3.5
        assert rows[0].edited is False
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_models_segment.py -v`
Expected: FAIL.

- [ ] **Step 3: Segment 모델 구현**

Write `backend/app/models/segment.py`:

```python
from sqlmodel import Field, SQLModel


class Segment(SQLModel, table=True):
    __tablename__ = "segment"

    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    idx: int
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    edited: bool = False
    words: str | None = None
```

Overwrite `backend/app/models/__init__.py`:

```python
from app.models.job import Job, JobStatus, SourceKind
from app.models.segment import Segment

__all__ = ["Job", "JobStatus", "SourceKind", "Segment"]
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_models_segment.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/models/
git commit -m "feat(backend): add Segment model with FK to Job"
```

---

### Task 1.4: DB 엔진 + WAL 모드 초기화

**Files:**
- Create: `backend/app/core/db.py`
- Create: `backend/tests/test_db.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_db.py`:

```python
from sqlalchemy import text

from app.core.db import create_db_engine, init_db


def test_init_db_creates_tables_and_enables_wal(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_db_engine(url)
    init_db(engine)

    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert mode.lower() == "wal"

        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        assert "job" in tables
        assert "segment" in tables
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_db.py -v`

- [ ] **Step 3: db 모듈 구현**

Write `backend/app/core/db.py`:

```python
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

import app.models  # noqa: F401  -- 메타데이터 등록 목적 import


def _ensure_parent_dir(url: str) -> None:
    if url.startswith("sqlite:///"):
        path = urlparse(url).path
        if path.startswith("/"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(url: str) -> Engine:
    _ensure_parent_dir(url)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/core/db.py backend/tests/test_db.py
git commit -m "feat(backend): add DB engine with WAL mode"
```

---

### Task 1.5: FastAPI 앱 + /api/health

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'h.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))

    app = create_app()
    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "disk_free" in body
    assert "model_cache_size" in body
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_health.py -v`

- [ ] **Step 3: health 라우터 + main 구현**

Write `backend/app/api/__init__.py` (빈 파일):

```python
```

Write `backend/app/api/health.py`:

```python
import shutil
from pathlib import Path

from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(prefix="/api", tags=["health"])


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


@router.get("/health")
def health() -> dict:
    s = get_settings()
    s.media_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(s.media_dir)
    return {
        "ok": True,
        "disk_free": usage.free,
        "model_cache_size": _dir_size(s.model_cache_dir),
        "role": s.gensub_role,
    }
```

Write `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.db import create_db_engine, init_db
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GenSub", version="0.1.0")

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
    return app


app = create_app()
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/main.py backend/app/api/ backend/tests/test_health.py
git commit -m "feat(backend): add FastAPI app with /api/health"
```

---

### Task 1.6: /api/config 엔드포인트

**Files:**
- Create: `backend/app/api/config.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_config_endpoint.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_config_endpoint.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_config_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'c.db'}")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("DEFAULT_MODEL", "small")

    client = TestClient(create_app())
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["default_model"] == "small"
    assert "tiny" in body["available_models"]
    assert "large-v3" in body["available_models"]
    assert body["max_video_minutes"] == 90
    assert body["has_openai_fallback"] is False
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_config_endpoint.py -v`

- [ ] **Step 3: config 라우터 구현**

Write `backend/app/api/config.py`:

```python
from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(prefix="/api", tags=["config"])

AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]


@router.get("/config")
def config() -> dict:
    s = get_settings()
    return {
        "default_model": s.default_model,
        "available_models": AVAILABLE_MODELS,
        "max_video_minutes": s.max_video_minutes,
        "max_upload_mb": s.max_upload_mb,
        "job_ttl_hours": s.job_ttl_hours,
        "has_openai_fallback": bool(s.openai_api_key),
    }
```

Modify `backend/app/main.py`: `from app.api.config import router as config_router` 임포트를 추가하고, `app.include_router(health_router)` 바로 아래에 `app.include_router(config_router)`를 추가.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/ -v`
Expected: 전체 그린.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/config.py backend/app/main.py backend/tests/test_config_endpoint.py
git commit -m "feat(backend): add /api/config endpoint"
```

---

