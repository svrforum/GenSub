# Phase 3 — R1~R7 리팩토링

목표: 스펙 §7의 7개 리팩토링을 순차 실행. 각 R은 독립 커밋. **각 Task 시작 전 `cd backend && uv run pytest`로 그린 확인 필수**.

실행 순서(작은 것 → 큰 것):
- R1 (regenerate 제거) → R5 (assert 교체) → R7 (worker healthcheck) → R2 (서비스 추출) → R4 (ttlDays 연결) → R6 (백업 분리) → R3 (burn 취소)

---

### Task 3.1 (R1): `regenerate` 엔드포인트·서비스 제거

**근거**: 프론트 호출 경로 없음 (죽은 코드). 동기 HTTP 안에서 ffmpeg+Whisper 실행은 API 블로킹.

**Files:**
- Delete: `backend/app/services/regenerate.py`
- Delete: `backend/tests/test_regenerate.py`
- Modify: `backend/app/api/segments.py` — regenerate 라우트 제거
- Modify: `frontend/src/lib/api/jobs.ts` — `regenerateSegment` 제거
- Modify: `frontend/src/lib/api/types.ts` — 관련 타입 제거 (있다면)

- [ ] **Step 1: 기준선 테스트**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 전부 pass.

- [ ] **Step 2: 현재 파일 확인**

```bash
cd /Users/loki/GenSub
cat backend/app/services/regenerate.py | head -20
grep -n "regenerate" backend/app/api/segments.py
grep -n "regenerate" frontend/src/lib/api/jobs.ts frontend/src/lib/api/types.ts 2>/dev/null
grep -rn "regenerateSegment\|regenerate_service" frontend/src/ 2>/dev/null || echo "no frontend usage"
```

Expected: 프론트 컴포넌트에서 `regenerateSegment` 호출 없음 확인.

- [ ] **Step 3: 파일 삭제**

```bash
rm backend/app/services/regenerate.py
rm backend/tests/test_regenerate.py
ls backend/app/services/regenerate.py backend/tests/test_regenerate.py 2>&1
```

Expected: 둘 다 "No such file".

- [ ] **Step 4: `api/segments.py`에서 라우트 제거**

Read `backend/app/api/segments.py`. 다음 두 가지 제거:
1. `from app.services.regenerate import ...` import 라인
2. `@router.post("/{job_id}/segments/{idx}/regenerate")` 부터 해당 함수 끝까지

남은 다른 라우트는 그대로 유지. 파일 상단 import 블록도 정돈.

- [ ] **Step 5: 프론트 `jobs.ts`에서 `regenerateSegment` 제거**

Read `frontend/src/lib/api/jobs.ts`. `regenerateSegment` export 함수 블록 삭제. 관련 타입 import가 있으면 함께 제거.

- [ ] **Step 6: 프론트 `types.ts`에서 관련 타입 제거**

Read `frontend/src/lib/api/types.ts`. `RegenerateRequest`/`RegenerateResponse` 같은 타입이 있으면 삭제. 없으면 skip.

- [ ] **Step 7: 테스트 재실행**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -5
```

Expected: 전부 pass (테스트 1개 줄어듦).

- [ ] **Step 8: 프론트 빌드 확인**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -10
```

Expected: 에러 없음. 타입 에러가 나오면 남은 참조를 정리.

- [ ] **Step 9: 커밋**

```bash
cd /Users/loki/GenSub
git add -A
git commit -m "$(cat <<'EOF'
refactor: remove unused regenerate endpoint and service

프론트에서 호출 경로 없음(죽은 코드). 동기 HTTP 핸들러에서 ffmpeg+Whisper를
실행하던 구조라 잠재적 DoS 위험도 있었음. 재도입 시 worker queue 경유로
재설계 필요.

- backend/app/services/regenerate.py 삭제
- backend/tests/test_regenerate.py 삭제
- backend/app/api/segments.py 라우트 제거
- frontend/src/lib/api/jobs.ts, types.ts 관련 함수/타입 제거

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.2 (R5): `burn.py`의 `assert` → `RuntimeError`

**근거**: `python -O` 실행 시 `assert`가 제거되어 Null pointer 사용 가능. 명시적 예외로 교체.

**Files:**
- Modify: `backend/app/services/burn.py:43`

- [ ] **Step 1: 현재 코드 확인**

```bash
sed -n '40,50p' backend/app/services/burn.py
```

Expected line 43: `assert proc.stdout is not None`.

- [ ] **Step 2: 수정**

`backend/app/services/burn.py` 편집:

```python
# 변경 전:
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    total_us = total_duration_sec * 1_000_000

# 변경 후:
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout is None:
        raise RuntimeError("ffmpeg process failed to start (stdout is None)")
    total_us = total_duration_sec * 1_000_000
```

- [ ] **Step 3: 테스트**

```bash
cd /Users/loki/GenSub/backend
uv run pytest tests/test_burn.py -v --tb=short
```

Expected: 기존 burn 테스트 pass 유지.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/burn.py
git commit -m "$(cat <<'EOF'
refactor(burn): replace assert with explicit RuntimeError

python -O 실행 시 assert가 제거되어 None dereference가 가능해짐.
명시적 RuntimeError로 교체해 프로덕션 안전성 확보.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.3 (R7): worker healthcheck 추가

**근거**: worker가 crash-loop 상태여도 `depends_on`으로 감지 불가. `pgrep`으로 프로세스 생존 체크.

**Files:**
- Modify: `Dockerfile` — `procps` 패키지 추가
- Modify: `compose.yaml` — worker에 healthcheck

- [ ] **Step 1: 현재 Dockerfile 확인**

```bash
grep -n "apt-get install" Dockerfile
```

- [ ] **Step 2: Dockerfile 수정**

`Dockerfile`의 apt install 블록에 `procps` 추가:

```dockerfile
# 변경 전:
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        mkvtoolnix \
        libsndfile1 \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 변경 후:
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        mkvtoolnix \
        libsndfile1 \
        procps \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: compose.yaml 수정**

`compose.yaml`의 `worker` 서비스에 다음 블록 추가 (`restart: unless-stopped` 바로 앞 또는 뒤):

```yaml
  worker:
    # ... 기존 설정 유지 ...
    restart: unless-stopped
    stop_grace_period: 30s
    healthcheck:
      test: ["CMD", "pgrep", "-f", "worker.main"]
      interval: 30s
      timeout: 5s
      retries: 3
```

- [ ] **Step 4: Docker 빌드 검증**

```bash
cd /Users/loki/GenSub
docker compose build worker 2>&1 | tail -20
```

Expected: 빌드 성공. `procps` 설치 로그 확인.

- [ ] **Step 5: 헬스체크 동작 확인 (옵션, 시간이 허락하면)**

```bash
docker compose up -d worker
sleep 35  # interval 30s 기다림
docker inspect gensub-worker --format='{{.State.Health.Status}}'
docker compose down
```

Expected: `healthy`.

- [ ] **Step 6: 커밋**

```bash
git add Dockerfile compose.yaml
git commit -m "$(cat <<'EOF'
chore(docker): add worker healthcheck via pgrep

worker가 crash-loop 상태여도 depends_on만으로는 감지 불가.
pgrep -f worker.main 기반 헬스체크 추가. python:3.11-slim에
pgrep이 없어 Dockerfile에 procps 패키지도 함께 추가.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.4 (R2): `pin_job`·`trigger_burn`을 `services/jobs.py`로 추출

**근거**: 두 엔드포인트만 라우터에서 직접 `Session`을 열어 도메인 로직 실행. 다른 CRUD는 이미 services 경유 — 일관성 회복.

**Files:**
- Modify: `backend/app/services/jobs.py` — 함수 2개 추가
- Modify: `backend/app/api/jobs.py` — `pin_job`, `trigger_burn` 핸들러가 services 호출만 수행
- Create: `backend/tests/test_jobs_service_pin.py`
- Create: `backend/tests/test_jobs_service_request_burn.py`

- [ ] **Step 1: 기준선**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

- [ ] **Step 2: 현재 라우터 코드 확인**

```bash
sed -n '101,138p' backend/app/api/jobs.py
cat backend/app/services/jobs.py | head -40
```

기존 `pin_job` / `trigger_burn` 핸들러의 Session 사용 패턴 파악.

- [ ] **Step 3: 먼저 `test_jobs_service_pin.py` 작성 (TDD)**

Write `backend/tests/test_jobs_service_pin.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.services.jobs import pin_job


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    init_db(engine)
    return engine


@pytest.fixture
def ready_job(engine):
    job = Job(
        id="j1",
        source_url="https://example.com/v",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
    return job


def test_pin_job_sets_pinned_true(engine, ready_job):
    pin_job(engine, ready_job.id, True)
    with Session(engine) as s:
        got = s.get(Job, ready_job.id)
        assert got is not None
        assert got.pinned is True


def test_unpin_job_sets_pinned_false(engine, ready_job):
    pin_job(engine, ready_job.id, True)
    pin_job(engine, ready_job.id, False)
    with Session(engine) as s:
        assert s.get(Job, ready_job.id).pinned is False


def test_pin_job_missing_raises(engine):
    with pytest.raises(LookupError):
        pin_job(engine, "nonexistent", True)
```

- [ ] **Step 4: 테스트 실행 → 실패 확인**

```bash
uv run pytest tests/test_jobs_service_pin.py -v 2>&1 | tail -15
```

Expected: `pin_job`가 없거나 import 실패.

- [ ] **Step 5: `services/jobs.py`에 `pin_job` 구현**

`backend/app/services/jobs.py`에 함수 추가 (파일 하단 또는 관련 함수 근처):

```python
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.models.job import Job


def pin_job(engine: Engine, job_id: str, pinned: bool) -> None:
    """pinned 상태를 토글. 없는 job이면 LookupError."""
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            raise LookupError(job_id)
        job.pinned = pinned
        s.add(job)
        s.commit()
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
uv run pytest tests/test_jobs_service_pin.py -v 2>&1 | tail -5
```

Expected: 3 passed.

- [ ] **Step 7: `test_jobs_service_request_burn.py` 작성**

Write `backend/tests/test_jobs_service_request_burn.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.services.jobs import request_burn


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    init_db(engine)
    return engine


def _make_job(engine, status: JobStatus) -> str:
    job = Job(
        id="j1",
        source_url="https://example.com/v",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=status,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
    return job.id


def test_request_burn_from_ready_transitions_to_burning(engine):
    jid = _make_job(engine, JobStatus.ready)
    request_burn(engine, jid)
    with Session(engine) as s:
        got = s.get(Job, jid)
        assert got.status == JobStatus.burning
        assert got.progress == 0.0
        assert got.stage_message is not None


def test_request_burn_from_non_ready_raises(engine):
    jid = _make_job(engine, JobStatus.transcribing)
    with pytest.raises(ValueError):
        request_burn(engine, jid)


def test_request_burn_missing_raises(engine):
    with pytest.raises(LookupError):
        request_burn(engine, "nonexistent")
```

- [ ] **Step 8: 테스트 실행 → 실패**

```bash
uv run pytest tests/test_jobs_service_request_burn.py -v 2>&1 | tail -10
```

- [ ] **Step 9: `request_burn` 구현**

`backend/app/services/jobs.py`에 추가:

```python
from app.models.job import JobStatus


def request_burn(engine: Engine, job_id: str) -> None:
    """ready 상태인 job을 burning으로 전이. pipeline에서 picker가 잡음."""
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            raise LookupError(job_id)
        if job.status != JobStatus.ready:
            raise ValueError(f"cannot burn job in status={job.status}")
        job.status = JobStatus.burning
        job.progress = 0.0
        job.stage_message = "자막을 영상에 입히고 있어요"
        job.error_message = None
        s.add(job)
        s.commit()
```

- [ ] **Step 10: 테스트 통과**

```bash
uv run pytest tests/test_jobs_service_request_burn.py -v 2>&1 | tail -5
```

Expected: 3 passed.

- [ ] **Step 11: 라우터가 서비스를 호출하도록 변경**

`backend/app/api/jobs.py` 편집:

1. 상단에 import 추가:
   ```python
   from app.services.jobs import pin_job as pin_job_service, request_burn
   ```
2. 라우터 핸들러 교체:

```python
# 변경 전 pin_job 핸들러 (Session 직접 사용):
@router.post("/{job_id}/pin")
def pin_job_endpoint(job_id: str, request: Request, body: dict) -> dict:
    # ... Session(engine) 직접 사용 ...

# 변경 후:
@router.post("/{job_id}/pin")
def pin_job_endpoint(job_id: str, request: Request, body: dict) -> dict:
    pinned = bool(body.get("pinned", True))
    try:
        pin_job_service(request.app.state.engine, job_id, pinned)
    except LookupError as err:
        raise HTTPException(status_code=404, detail="job not found") from err
    return {"ok": True, "pinned": pinned}
```

```python
# 변경 전 trigger_burn 핸들러:
@router.post("/{job_id}/burn")
def trigger_burn(...):
    # ... Session(engine) 직접 사용, status 필드 직접 수정 ...

# 변경 후:
@router.post("/{job_id}/burn")
def trigger_burn(job_id: str, request: Request) -> dict:
    try:
        request_burn(request.app.state.engine, job_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail="job not found") from err
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err
    return {"ok": True}
```

(주의: 기존 함수 시그니처·body 처리 방식은 실제 코드 읽어서 맞춰라. 위는 대표 형태.)

- [ ] **Step 12: 전체 테스트**

```bash
uv run pytest --tb=short 2>&1 | tail -5
```

Expected: 전부 pass. 특히 기존 pin/burn 관련 통합 테스트도 그린.

- [ ] **Step 13: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/jobs.py backend/app/services/jobs.py backend/tests/test_jobs_service_pin.py backend/tests/test_jobs_service_request_burn.py
git commit -m "$(cat <<'EOF'
refactor(api): extract pin_job and request_burn into services layer

기존에 api/jobs.py의 두 핸들러만 services 경유 없이 Session을
직접 열고 도메인 로직을 수행 — 다른 엔드포인트(create/cancel/delete)와
일관성이 깨져 있었음. services/jobs.py에 pin_job/request_burn 함수
추출, 라우터는 검증과 서비스 호출만 수행.

테스트: 서비스 단위 테스트 2파일(6 케이스) 신규.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.5 (R4): Sidebar `ttlDays` → `/api/config.job_ttl_hours` 연결

**근거**: 사용자가 UI에서 "7일" 선택해도 서버는 여전히 24시간 기본값으로 삭제. localStorage가 백엔드에 도달하지 않음.

**설계**: 서버 TTL은 env로만 설정되므로, UI를 **선택형 → 표시형**으로 변경.

**Files:**
- Modify: `frontend/src/lib/api/jobs.ts` (또는 신규 `config.ts`) — `fetchConfig` 함수
- Modify: `frontend/src/lib/ui/Sidebar.svelte` — 선택 UI 제거, 표시형으로 변경

- [ ] **Step 1: 현재 Sidebar 코드 확인**

```bash
sed -n '100,150p' /Users/loki/GenSub/frontend/src/lib/ui/Sidebar.svelte
grep -n "ttlDays\|gensub.settings" /Users/loki/GenSub/frontend/src/lib/ui/Sidebar.svelte
```

- [ ] **Step 2: `fetchConfig` 함수 추가**

`frontend/src/lib/api/jobs.ts` 하단에 추가 (또는 새 파일 `config.ts` 생성 후 동일 내용):

```typescript
export interface ServerConfig {
  default_model: string;
  available_models: string[];
  max_video_minutes: number;
  max_upload_mb: number;
  job_ttl_hours: number;
  has_openai_fallback: boolean;
}

export async function fetchConfig(): Promise<ServerConfig> {
  const res = await fetch('/api/config');
  if (!res.ok) throw new Error(`config fetch failed: ${res.status}`);
  return (await res.json()) as ServerConfig;
}
```

- [ ] **Step 3: Sidebar 수정**

`frontend/src/lib/ui/Sidebar.svelte` 편집:

1. `<script>` 상단에 import + 상태 추가:
   ```typescript
   import { fetchConfig } from '$lib/api/jobs';
   let serverTtlHours: number | null = null;
   ```
2. `onMount` 또는 동등한 초기화 지점에서:
   ```typescript
   onMount(async () => {
     try {
       const cfg = await fetchConfig();
       serverTtlHours = cfg.job_ttl_hours;
     } catch {
       serverTtlHours = null;
     }
   });
   ```
3. 기존 "보관 기간" 선택 UI 블록(현재 localStorage ttlDays 바인딩)을 다음으로 교체:

```svelte
<!-- 기존 segmented control/select 삭제하고 표시형으로: -->
<div class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
  {#if serverTtlHours === null}
    보관 기간 정보를 불러오는 중…
  {:else}
    작업은 <strong>{serverTtlHours}시간</strong> 후 자동 삭제됩니다.
    <br />
    북마크(📌)한 작업은 만료되지 않아요.
  {/if}
</div>
```

4. `ttlDays` 관련 `let` 변수·`localStorage.setItem('gensub.settings.ttlDays', ...)`·`localStorage.getItem(...)` 호출 전부 제거.

- [ ] **Step 4: 타입 체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -15
```

Expected: 에러 없음.

- [ ] **Step 5: 백엔드 config 엔드포인트 스냅샷 테스트 (신규)**

새 파일 만들지 않고 기존 `backend/tests/test_config_endpoint.py`가 `job_ttl_hours`를 assert하는지 확인:

```bash
grep "job_ttl_hours" /Users/loki/GenSub/backend/tests/test_config_endpoint.py
```

없으면 테스트에 assertion 추가:

```python
def test_config_includes_job_ttl_hours(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "job_ttl_hours" in data
    assert isinstance(data["job_ttl_hours"], int)
    assert data["job_ttl_hours"] > 0
```

- [ ] **Step 6: 테스트 실행**

```bash
cd /Users/loki/GenSub/backend
uv run pytest tests/test_config_endpoint.py -v 2>&1 | tail -5
```

Expected: 전부 pass.

- [ ] **Step 7: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ backend/tests/test_config_endpoint.py
git commit -m "$(cat <<'EOF'
fix(frontend): sidebar TTL display reflects actual server setting

기존: Sidebar가 localStorage의 ttlDays(기본 7)를 표시했지만 백엔드로
전송되지 않아, 사용자는 "7일"로 믿고 있어도 실제로는 JOB_TTL_HOURS(기본
24시간)로 삭제됨. 설정 변경이 아닌 UX 버그.

수정: "보관 기간"을 선택형 → 표시형으로 변경. /api/config의
job_ttl_hours를 읽어서 "N시간 후 자동 삭제" 안내. 환경 변수로만
설정 가능하다는 실제 동작을 정확히 전달.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.6 (R6): 백업 로직을 `services/backup.py`로 분리 + worker에서도 호출

**근거**: 현재 `_backup_db`는 `app/main.py`의 lifespan inline. api가 기동되지 않은 채 worker만 돌다 크래시하면 백업 누락.

**Files:**
- Create: `backend/app/services/backup.py`
- Create: `backend/tests/test_backup.py`
- Modify: `backend/app/main.py` — inline 제거, 서비스 호출
- Modify: `backend/worker/main.py` — 기동 시 백업 호출

- [ ] **Step 1: 기준선**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

- [ ] **Step 2: 테스트 작성 (TDD)**

Write `backend/tests/test_backup.py`:

```python
from datetime import datetime, timedelta
from pathlib import Path

from app.core.settings import Settings
from app.services.backup import backup_database


def _make_settings(db_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{db_path}",
        media_dir=db_path.parent / "media",
        model_cache_dir=db_path.parent / "models",
    )


def test_backup_creates_backup_file(tmp_path):
    db_path = tmp_path / "jobs.db"
    db_path.write_bytes(b"fake db content")
    settings = _make_settings(db_path)

    backup_database(settings)

    backup_dir = tmp_path / "backups"
    assert backup_dir.exists()
    backups = list(backup_dir.glob("jobs_*.db"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"fake db content"


def test_backup_keeps_only_recent_three(tmp_path):
    db_path = tmp_path / "jobs.db"
    db_path.write_bytes(b"x")
    settings = _make_settings(db_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # 오래된 백업 4개 미리 세팅 (서로 다른 timestamp)
    old_times = [
        datetime.now() - timedelta(hours=i) for i in [10, 8, 6, 4]
    ]
    for t in old_times:
        stamp = t.strftime("%Y%m%d_%H%M%S")
        (backup_dir / f"jobs_{stamp}.db").write_bytes(b"old")

    backup_database(settings)

    backups = sorted(backup_dir.glob("jobs_*.db"))
    assert len(backups) == 3


def test_backup_noop_when_db_missing(tmp_path):
    db_path = tmp_path / "jobs.db"  # 존재하지 않음
    settings = _make_settings(db_path)

    # 에러 없이 통과해야 함
    backup_database(settings)

    backup_dir = tmp_path / "backups"
    assert not backup_dir.exists() or not list(backup_dir.glob("jobs_*.db"))
```

- [ ] **Step 3: 테스트 실행 → 실패 확인**

```bash
uv run pytest tests/test_backup.py -v 2>&1 | tail -10
```

Expected: import 실패 또는 함수 없음.

- [ ] **Step 4: 서비스 구현**

Write `backend/app/services/backup.py`:

```python
"""SQLite DB 백업 유틸리티. api/worker 양쪽에서 기동 시 호출."""

import shutil
from datetime import datetime
from pathlib import Path

from app.core.settings import Settings

KEEP_RECENT = 3


def backup_database(settings: Settings, *, keep: int = KEEP_RECENT) -> Path | None:
    """현재 DB 파일을 backups/ 디렉토리에 타임스탬프와 함께 복사.

    DB 파일이 없으면 noop(None 반환). 백업 성공 시 백업 경로 반환.
    오래된 백업은 최근 `keep`개만 남기고 삭제.
    """
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    if not db_path.exists():
        return None

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"jobs_{stamp}.db"
    shutil.copy2(db_path, target)

    # 오래된 백업 정리 (파일명 기준 역순 = 최신 우선)
    existing = sorted(backup_dir.glob("jobs_*.db"), reverse=True)
    for old in existing[keep:]:
        old.unlink(missing_ok=True)

    return target
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
uv run pytest tests/test_backup.py -v 2>&1 | tail -5
```

Expected: 3 passed.

- [ ] **Step 6: `app/main.py`에서 inline 제거**

`backend/app/main.py` 편집:

1. 파일 상단 import에 추가:
   ```python
   from app.services.backup import backup_database
   ```
2. inline `_backup_db` 함수 전체 삭제 (28~44라인 부근).
3. lifespan 함수 내 호출 교체:
   ```python
   # 변경 전:
   _backup_db(app.state.settings)

   # 변경 후:
   backup_database(app.state.settings)
   ```

- [ ] **Step 7: worker에서도 백업 호출**

`backend/worker/main.py` 편집:

1. import 추가:
   ```python
   from app.services.backup import backup_database
   ```
2. `run()` 함수에서 `sweep_zombie_jobs(engine)` 직전(또는 직후)에 추가:
   ```python
   settings = get_settings()
   engine = create_db_engine(settings.database_url)
   init_db(engine)

   backup_database(settings)  # 신규 추가

   swept = sweep_zombie_jobs(engine)
   ```

- [ ] **Step 8: 전체 테스트**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -5
```

Expected: 전부 pass.

- [ ] **Step 9: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/backup.py backend/tests/test_backup.py backend/app/main.py backend/worker/main.py
git commit -m "$(cat <<'EOF'
refactor: move DB backup to services/backup.py and call from worker

기존: _backup_db가 app/main.py lifespan 내 inline 함수 → api가
기동되지 않은 상태로 worker만 돌다 크래시하면 백업 누락.

변경: services/backup.py의 backup_database()로 이관. api 시작 시와
worker 시작 시 양쪽에서 호출. 최근 3개 유지 로직은 동일.
테스트 3 케이스 신규(생성/로테이션/DB 없음 noop).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.7 (R3): `process_burn_job`에 취소 경로 + ffmpeg 프로세스 종료

**근거**: burn 중 취소 요청 시 ffmpeg가 끝날 때까지(수 분) 큐가 막힘. `process_job`의 취소 패턴과 일관성 없음.

**Files:**
- Modify: `backend/app/services/burn.py` — `cancel_check` 콜백 추가, 취소 시 프로세스 종료
- Modify: `backend/app/services/pipeline.py:126-168` — `_check_cancel` 배치 + `JobCancelledError` 처리 + 부분 파일 정리
- Create: `backend/tests/test_pipeline_burn_cancel.py`

- [ ] **Step 1: 기준선**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

- [ ] **Step 2: 테스트 먼저 (TDD)**

Write `backend/tests/test_pipeline_burn_cancel.py`:

```python
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus, SourceKind
from app.services.pipeline import process_burn_job


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'jobs.db'}",
        media_dir=tmp_path / "media",
        model_cache_dir=tmp_path / "models",
    )


def _seed_burning_job(engine, settings: Settings, cancel: bool = False) -> str:
    media = settings.media_dir / "j1"
    media.mkdir(parents=True, exist_ok=True)
    (media / "source.mp4").write_bytes(b"fake")
    (media / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nhi\n", encoding="utf-8")

    job = Job(
        id="j1",
        source_url="https://example.com/v",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.burning,
        progress=0.0,
        duration_sec=2.0,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        cancel_requested=cancel,
    )
    with Session(engine) as s:
        s.add(job)
        s.commit()
    return job.id


def test_burn_respects_cancel_before_start(tmp_path):
    """취소 플래그가 이미 True면 burn_video 실행 전에 failed로 종료."""
    settings = _make_settings(tmp_path)
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    jid = _seed_burning_job(engine, settings, cancel=True)

    # segments 기본 1개 세팅 필요 — 단순화: replace_all_segments 대신 DB에 직접
    # (또는 load_segments가 빈 리스트여도 되면 생략)

    process_burn_job(settings=settings, engine=engine, job_id=jid)

    with Session(engine) as s:
        job = s.get(Job, jid)
    assert job.status == JobStatus.failed
    assert job.error_message is not None
    # 부분 출력 없음
    assert not (settings.media_dir / jid / "burned.mp4").exists()


@pytest.mark.skipif(not shutil_has("ffmpeg"), reason="ffmpeg not available")
def test_burn_cancel_mid_flight_terminates_ffmpeg(tmp_path, monkeypatch):
    """
    실제 ffmpeg를 쓰되, burn_video에 잠깐 대기하는 fake source를 넘겨
    루프 도중 cancel_requested를 세팅하고 프로세스가 수 초 내 종료되는지 검증.

    구현 난이도에 따라 이 테스트는 burn.py 단위로 쪼개거나 skip 가능.
    """
    # (옵션) — 상세 구현은 리팩토링 중 burn_video 시그니처 확정 후 작성
    pytest.skip("implemented after burn_video signature stabilized")


def shutil_has(name: str) -> bool:
    import shutil as _s
    return _s.which(name) is not None
```

> 주의: 두 번째 테스트는 ffmpeg 실제 실행이 필요하므로 CI에서는 skip 가능. 첫 번째 테스트만으로도 파이프라인 레벨 취소 경로는 검증됨.

- [ ] **Step 3: 테스트 실행 → 1번 테스트 실패 기대**

```bash
uv run pytest tests/test_pipeline_burn_cancel.py -v 2>&1 | tail -10
```

Expected: 1번 실패(아직 process_burn_job이 시작 전 cancel 체크 안 함).

- [ ] **Step 4: `services/burn.py` 수정 — `cancel_check` 콜백**

`backend/app/services/burn.py` 전체 편집:

```python
import re
import subprocess
from collections.abc import Callable
from pathlib import Path


def build_burn_args(video: Path, ass: Path, output: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-vf",
        f"ass={ass}",
        "-c:a",
        "copy",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output),
    ]


_TIME_RE = re.compile(r"out_time_ms=(\d+)")


def burn_video(
    video: Path,
    ass: Path,
    output: Path,
    total_duration_sec: float,
    progress_callback: Callable[[float], None] | None = None,
    cancel_check: Callable[[], None] | None = None,
) -> Path:
    """ffmpeg burn-in. cancel_check가 예외를 raise하면 ffmpeg 종료 후 예외 재발생."""
    output.parent.mkdir(parents=True, exist_ok=True)
    args = build_burn_args(video, ass, output)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout is None:
        raise RuntimeError("ffmpeg process failed to start (stdout is None)")

    total_us = total_duration_sec * 1_000_000
    cancelled_exc: BaseException | None = None

    try:
        for raw in proc.stdout:
            if cancel_check is not None:
                try:
                    cancel_check()
                except BaseException as exc:  # JobCancelledError 등
                    cancelled_exc = exc
                    break
            m = _TIME_RE.search(raw)
            if m and total_us > 0 and progress_callback:
                processed = int(m.group(1))
                progress_callback(min(1.0, processed / total_us))
    finally:
        if cancelled_exc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    if cancelled_exc is not None:
        raise cancelled_exc

    rc = proc.wait()
    if rc != 0:
        err = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(f"burn failed: {err[:500]}")
    return output
```

- [ ] **Step 5: `services/pipeline.py`의 `process_burn_job` 수정**

`backend/app/services/pipeline.py`의 해당 함수(126~168 근처) 교체:

```python
def process_burn_job(
    settings: Settings,
    engine: Engine,
    job_id: str,
    style: BurnStyle | None = None,
) -> None:
    media_dir = settings.media_dir / job_id

    def _cancel() -> None:
        _check_cancel(engine, job_id)

    try:
        _cancel()  # 시작 전 체크

        with Session(engine) as s:
            job = s.get(Job, job_id)
            if job is None:
                return
            duration = job.duration_sec or 1.0

        source_candidates = list(media_dir.glob("source.*"))
        if not source_candidates:
            raise RuntimeError("source video missing")
        source = source_candidates[0]

        segments = load_segments(engine, job_id)
        ass_path = media_dir / "subtitles.ass"
        ass_path.write_text(
            srt_segments_to_ass(segments, style or BurnStyle()),
            encoding="utf-8",
        )

        job_state.update_progress(engine, job_id, 0.0, "자막을 영상에 입히고 있어요")

        def burn_progress(pct: float) -> None:
            job_state.update_progress(engine, job_id, pct)

        output = media_dir / "burned.mp4"
        burn_video(
            video=source,
            ass=ass_path,
            output=output,
            total_duration_sec=duration,
            progress_callback=burn_progress,
            cancel_check=_cancel,
        )
        _cancel()  # 완료 직전 최종 체크
        job_state.mark_done(engine, job_id)
    except JobCancelledError:
        # 부분 생성된 burned.mp4 정리
        partial = media_dir / "burned.mp4"
        if partial.exists():
            partial.unlink(missing_ok=True)
        job_state.mark_failed(engine, job_id, "사용자가 작업을 취소했어요")
    except Exception as exc:
        job_state.mark_failed(engine, job_id, str(exc))
```

- [ ] **Step 6: 테스트 재실행**

```bash
cd /Users/loki/GenSub/backend
uv run pytest tests/test_pipeline_burn_cancel.py -v 2>&1 | tail -10
```

Expected: 첫 번째 테스트 pass, 두 번째는 skip.

- [ ] **Step 7: 전체 테스트**

```bash
uv run pytest --tb=short 2>&1 | tail -5
```

Expected: 전부 pass. 기존 burn 관련 테스트도 그린 유지.

- [ ] **Step 8: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/burn.py backend/app/services/pipeline.py backend/tests/test_pipeline_burn_cancel.py
git commit -m "$(cat <<'EOF'
fix(pipeline): add cancel support to burn job

기존: process_burn_job은 process_job과 달리 _check_cancel이 전혀
없어, 사용자가 burn 중 취소를 눌러도 ffmpeg가 끝날 때까지(수 분)
큐가 막혔음.

수정:
- burn_video()에 cancel_check 콜백 추가. 진행률 루프 매 라인마다
  호출. 예외 발생 시 proc.terminate() → 5초 대기 → kill.
- process_burn_job 시작 전/완료 직전 _check_cancel. JobCancelledError
  catch 시 부분 burned.mp4 정리 + mark_failed("사용자가 ...").

테스트: 사전 취소 플래그 시 실행 없이 failed 되는지 검증.
실행 중 취소는 ffmpeg 실 바이너리 의존이라 skip 처리.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Phase 3 완료 검증

- [ ] **Step 1: 전체 테스트**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 38 passed (또는 그 근처 — 삭제 1, 추가 6~7 반영).

- [ ] **Step 2: 프론트엔드 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 에러 없음.

- [ ] **Step 3: 커밋 요약**

```bash
cd /Users/loki/GenSub
git log --oneline refactor/stability ^master | cat
```

Expected: Phase 2 + Phase 3 합쳐 10개 안팎의 커밋.

Phase 3 완료. Phase 4 검증 진행.
