# Phase 2 — Backend: API 엔드포인트 + Job 삭제 cascade

목표: Phase 1의 서비스 함수를 감싸는 FastAPI 라우터와, Job 삭제 시 Memo cascade 통합.

**전제**: Phase 1 완료, pytest 120 passed, `feature/memo` 브랜치.

---

### Task 2.1: 기준선 + API 스키마 작성

**Files:**
- Modify: `backend/app/api/schemas.py` (MemoOut, MemoPatchRequest 추가)
- Create: `backend/tests/test_memo_schemas.py`

- [ ] **Step 1: 기준선**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 120 passed.

- [ ] **Step 2: 현재 schemas.py 확인**

```bash
cat backend/app/api/schemas.py
```

기존 BaseModel 패턴 확인.

- [ ] **Step 3: 테스트 작성**

Write `backend/tests/test_memo_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.api.schemas import MemoPatchRequest


def test_memo_patch_accepts_empty_string():
 req = MemoPatchRequest(memo_text="")
 assert req.memo_text == ""


def test_memo_patch_accepts_500_chars():
 req = MemoPatchRequest(memo_text="x" * 500)
 assert len(req.memo_text) == 500


def test_memo_patch_rejects_over_500_chars():
 with pytest.raises(ValidationError):
 MemoPatchRequest(memo_text="x" * 501)


def test_memo_patch_rejects_missing_field():
 with pytest.raises(ValidationError):
 MemoPatchRequest()
```

- [ ] **Step 4: 실패 확인**

```bash
uv run pytest tests/test_memo_schemas.py -v 2>&1 | tail -10
```

- [ ] **Step 5: 스키마 추가**

Read `backend/app/api/schemas.py`, 파일 말미에 추가:

```python
from pydantic import BaseModel, Field


class MemoPatchRequest(BaseModel):
 memo_text: str = Field(min_length=0, max_length=500)
```

(import가 이미 있으면 중복 제거.)

- [ ] **Step 6: 통과 확인**

```bash
uv run pytest tests/test_memo_schemas.py -v 2>&1 | tail -10
```

Expected: 4 passed.

- [ ] **Step 7: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/schemas.py backend/tests/test_memo_schemas.py
git commit -m "$(cat <<'EOF'
feat(memo): add MemoPatchRequest schema with 500-char limit

Pydantic 레벨에서 memo_text 길이 500자 강제 (SQLite가 DB level 미강제
이므로 API 입구에서 방어).
EOF
)"
```

---

### Task 2.2: POST `/api/jobs/{job_id}/segments/{idx}/memo` + 라우터 등록

**Files:**
- Create: `backend/app/api/memo.py`
- Modify: `backend/app/main.py` (라우터 등록)
- Create: `backend/tests/test_memo_endpoint_post.py`

- [ ] **Step 1: main.py 의 기존 라우터 등록 패턴 확인**

```bash
grep -n "include_router" backend/app/main.py
```

- [ ] **Step 2: 테스트 작성**

Write `backend/tests/test_memo_endpoint_post.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.main import create_app
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment


@pytest.fixture
def client(tmp_path, monkeypatch):
 db_path = tmp_path / "jobs.db"
 monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 from app.core.settings import get_settings
 get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None

 app = create_app()
 return TestClient(app)


def _seed(client: TestClient):
 from app.main import create_app # noqa: F401
 engine = client.app.state.engine
 job = Job(
 id="job1",
 source_url="https://e/1",
 source_kind=SourceKind.url.value,
 model_name="small",
 status=JobStatus.ready,
 title="Test",
 expires_at=datetime.now(UTC) + timedelta(hours=24),
 pinned=False,
 )
 seg = Segment(
 job_id="job1", idx=3,
 start=10.0, end=12.5,
 text="Hello world",
 )
 with Session(engine) as session:
 session.add(job)
 session.add(seg)
 session.commit()


def test_post_creates_memo_201(client):
 _seed(client)
 resp = client.post("/api/jobs/job1/segments/3/memo")
 assert resp.status_code == 201
 body = resp.json()
 assert body["ok"] is True
 assert body["action"] == "created"
 assert body["memo"]["memo_text"] == ""
 assert body["memo"]["segment_text_snapshot"] == "Hello world"
 assert body["memo"]["job_id"] == "job1"


def test_post_toggles_off_when_empty_200(client):
 _seed(client)
 client.post("/api/jobs/job1/segments/3/memo")
 resp = client.post("/api/jobs/job1/segments/3/memo")
 assert resp.status_code == 200
 body = resp.json()
 assert body["action"] == "deleted"


def test_post_409_when_memo_has_text(client):
 _seed(client)
 first = client.post("/api/jobs/job1/segments/3/memo").json()
 client.patch(f"/api/memos/{first['memo']['id']}", json={"memo_text": "keep me"})

 resp = client.post("/api/jobs/job1/segments/3/memo")
 assert resp.status_code == 409
 body = resp.json()
 assert body["detail"]["reason"] == "memo_has_text"
 assert body["detail"]["memo_id"] == first["memo"]["id"]


def test_post_404_when_segment_missing(client):
 _seed(client)
 resp = client.post("/api/jobs/job1/segments/999/memo")
 assert resp.status_code == 404


def test_post_404_when_job_missing(client):
 resp = client.post("/api/jobs/nonexistent/segments/0/memo")
 assert resp.status_code == 404


def test_post_auto_pins_job(client):
 _seed(client)
 client.post("/api/jobs/job1/segments/3/memo")
 engine = client.app.state.engine
 with Session(engine) as session:
 job = session.get(Job, "job1")
 assert job.pinned is True
```

- [ ] **Step 3: 실행 → 실패**

```bash
uv run pytest tests/test_memo_endpoint_post.py -v 2>&1 | tail -15
```

- [ ] **Step 4: 라우터 구현**

Write `backend/app/api/memo.py`:

```python
from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas import MemoPatchRequest
from app.services import memo as memo_service

router = APIRouter(tags=["memos"])


def _memo_to_dict(memo) -> dict:
 return {
 "id": memo.id,
 "job_id": memo.job_id,
 "segment_idx": memo.segment_idx,
 "memo_text": memo.memo_text,
 "segment_text_snapshot": memo.segment_text_snapshot,
 "segment_start": memo.segment_start,
 "segment_end": memo.segment_end,
 "job_title_snapshot": memo.job_title_snapshot,
 "created_at": memo.created_at.isoformat(),
 "updated_at": memo.updated_at.isoformat(),
 }


@router.post("/api/jobs/{job_id}/segments/{idx}/memo")
def toggle_memo(job_id: str, idx: int, request: Request):
 engine = request.app.state.engine
 try:
 result = memo_service.toggle_save_memo(engine, job_id, idx)
 except LookupError as err:
 raise HTTPException(status_code=404, detail=str(err)) from err

 if result.action == "conflict":
 raise HTTPException(
 status_code=409,
 detail={"reason": "memo_has_text", "memo_id": result.memo.id},
 )

 if result.action == "created":
 return {
 "ok": True,
 "action": "created",
 "memo": _memo_to_dict(result.memo),
 }

 return {"ok": True, "action": "deleted"}


@router.patch("/api/memos/{memo_id}")
def patch_memo(memo_id: int, body: MemoPatchRequest, request: Request):
 engine = request.app.state.engine
 updated = memo_service.update_memo_text(engine, memo_id, body.memo_text)
 if updated is None:
 raise HTTPException(status_code=404, detail="memo not found")
 return {"ok": True, "memo": _memo_to_dict(updated)}
```

FastAPI의 POST 기본 status는 200. 새 메모 생성 시 201이 되도록 라우터에 `status_code=status.HTTP_201_CREATED` 를 **걸지 말고**, 대신 `Response` 조작이 필요. 단순화를 위해 라우터 설정을 수정:

```python
# 위 @router.post(...) 줄을 교체:
@router.post("/api/jobs/{job_id}/segments/{idx}/memo")
def toggle_memo(job_id: str, idx: int, request: Request, response: Response):
 engine = request.app.state.engine
 try:
 result = memo_service.toggle_save_memo(engine, job_id, idx)
 except LookupError as err:
 raise HTTPException(status_code=404, detail=str(err)) from err

 if result.action == "conflict":
 raise HTTPException(
 status_code=409,
 detail={"reason": "memo_has_text", "memo_id": result.memo.id},
 )

 if result.action == "created":
 response.status_code = status.HTTP_201_CREATED
 return {
 "ok": True,
 "action": "created",
 "memo": _memo_to_dict(result.memo),
 }

 return {"ok": True, "action": "deleted"}
```

import 추가: `from fastapi import APIRouter, HTTPException, Request, Response, status`.

- [ ] **Step 5: `main.py` 에 라우터 등록**

Read `backend/app/main.py`, 기존 `app.include_router(...)` 패턴 근처에 추가:

```python
from app.api.memo import router as memo_router
# ...
app.include_router(memo_router)
```

- [ ] **Step 6: 통과 확인**

```bash
uv run pytest tests/test_memo_endpoint_post.py -v 2>&1 | tail -15
```

Expected: 6 passed.

- [ ] **Step 7: 전체 테스트**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 130 passed (120 + 4 schemas + 6 POST endpoint).

- [ ] **Step 8: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/memo.py backend/app/main.py backend/tests/test_memo_endpoint_post.py
git commit -m "$(cat <<'EOF'
feat(memo): add POST /api/jobs/{id}/segments/{idx}/memo endpoint

스펙 §4.2 toggle-save + PATCH /api/memos/{id} (스키마 검증).

- 생성: 201 + 응답에 memo 전체
- 삭제: 200 + action=deleted
- conflict: 409 + detail={reason:"memo_has_text", memo_id:N}
- 404: job/segment 없음

라우터는 services.memo만 호출 (CLAUDE.md §2 레이어 규칙).
EOF
)"
```

---

### Task 2.3: GET 전역/Job별 + DELETE

**Files:**
- Modify: `backend/app/api/memo.py`
- Create: `backend/tests/test_memo_endpoint_list.py`
- Create: `backend/tests/test_memo_endpoint_delete.py`

- [ ] **Step 1: 리스트 테스트 작성**

Write `backend/tests/test_memo_endpoint_list.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment


@pytest.fixture
def client(tmp_path, monkeypatch):
 db_path = tmp_path / "jobs.db"
 monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 app = create_app()
 return TestClient(app)


def _seed_job(client, job_id="job1", title="Test"):
 engine = client.app.state.engine
 job = Job(
 id=job_id,
 source_url=f"https://e/{job_id}",
 source_kind=SourceKind.url.value,
 model_name="small",
 status=JobStatus.ready,
 title=title,
 expires_at=datetime.now(UTC) + timedelta(hours=24),
 )
 with Session(engine) as session:
 session.add(job)
 session.commit()


def _seed_segment(client, job_id, idx, text):
 engine = client.app.state.engine
 with Session(engine) as session:
 session.add(Segment(
 job_id=job_id, idx=idx,
 start=float(idx), end=float(idx) + 1,
 text=text,
 ))
 session.commit()


def _seed_memo(client, job_id, idx, memo_text=""):
 engine = client.app.state.engine
 with Session(engine) as session:
 m = Memo(
 job_id=job_id, segment_idx=idx,
 memo_text=memo_text,
 segment_text_snapshot=f"snap {idx}",
 segment_start=float(idx), segment_end=float(idx) + 1,
 job_title_snapshot="T",
 )
 session.add(m)
 session.commit()
 session.refresh(m)
 return m.id


def test_get_global_empty(client):
 resp = client.get("/api/memos")
 assert resp.status_code == 200
 assert resp.json() == {"items": []}


def test_get_global_includes_liveness(client):
 _seed_job(client)
 _seed_segment(client, "job1", 0, "current text")
 _seed_memo(client, "job1", 0)

 resp = client.get("/api/memos")
 assert resp.status_code == 200
 items = resp.json()["items"]
 assert len(items) == 1
 item = items[0]
 assert item["job_id"] == "job1"
 assert item["segment_text"] == "current text"
 assert item["job_alive"] is True


def test_get_global_orphan_shows_snapshot(client):
 _seed_memo(client, "orphan_job", 0)

 resp = client.get("/api/memos")
 [item] = resp.json()["items"]
 assert item["job_alive"] is False
 assert item["segment_text"] == "snap 0"


def test_get_global_limit(client):
 _seed_job(client)
 for i in range(5):
 _seed_segment(client, "job1", i, f"t{i}")
 _seed_memo(client, "job1", i)

 resp = client.get("/api/memos?limit=3")
 assert resp.status_code == 200
 assert len(resp.json()["items"]) == 3


def test_get_job_memos_returns_list(client):
 _seed_job(client)
 for i in (0, 2):
 _seed_segment(client, "job1", i, f"t{i}")
 _seed_memo(client, "job1", i)
 _seed_job(client, job_id="other")
 _seed_segment(client, "other", 0, "z")
 _seed_memo(client, "other", 0)

 resp = client.get("/api/jobs/job1/memos")
 assert resp.status_code == 200
 items = resp.json()["items"]
 assert {i["segment_idx"] for i in items} == {0, 2}
```

- [ ] **Step 2: 실패 확인**

```bash
uv run pytest tests/test_memo_endpoint_list.py -v 2>&1 | tail -10
```

- [ ] **Step 3: 라우터에 GET 추가**

`backend/app/api/memo.py` 말미에 추가:

```python
@router.get("/api/memos")
def list_memos(request: Request, limit: int = 100):
 engine = request.app.state.engine
 views = memo_service.list_all_memos_with_liveness(engine, limit=limit)
 return {
 "items": [
 {
 "id": v.id,
 "job_id": v.job_id,
 "segment_idx": v.segment_idx,
 "memo_text": v.memo_text,
 "segment_text": v.segment_text,
 "start": v.start,
 "end": v.end,
 "job_title": v.job_title,
 "job_alive": v.job_alive,
 "created_at": v.created_at.isoformat(),
 "updated_at": v.updated_at.isoformat(),
 }
 for v in views
 ]
 }


@router.get("/api/jobs/{job_id}/memos")
def list_memos_for_job(job_id: str, request: Request):
 engine = request.app.state.engine
 memos = memo_service.list_memos_for_job(engine, job_id)
 return {
 "items": [
 {
 "id": m.id,
 "job_id": m.job_id,
 "segment_idx": m.segment_idx,
 "memo_text": m.memo_text,
 }
 for m in memos
 ]
 }
```

- [ ] **Step 4: GET 테스트 통과 확인**

```bash
uv run pytest tests/test_memo_endpoint_list.py -v 2>&1 | tail -10
```

Expected: 5 passed.

- [ ] **Step 5: DELETE 테스트 작성**

Write `backend/tests/test_memo_endpoint_delete.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import create_app
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo


@pytest.fixture
def client(tmp_path, monkeypatch):
 db_path = tmp_path / "jobs.db"
 monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 app = create_app()
 return TestClient(app)


def _seed_memo(client) -> int:
 engine = client.app.state.engine
 job = Job(
 id="job1",
 source_url="https://e/1",
 source_kind=SourceKind.url.value,
 model_name="small",
 status=JobStatus.ready,
 title="T",
 expires_at=datetime.now(UTC) + timedelta(hours=24),
 )
 memo = Memo(
 job_id="job1", segment_idx=0,
 memo_text="note",
 segment_text_snapshot="s",
 segment_start=0, segment_end=1,
 )
 with Session(engine) as session:
 session.add(job)
 session.add(memo)
 session.commit()
 session.refresh(memo)
 return memo.id


def test_delete_memo_removes(client):
 mid = _seed_memo(client)
 resp = client.delete(f"/api/memos/{mid}")
 assert resp.status_code == 200
 assert resp.json() == {"ok": True}

 resp2 = client.delete(f"/api/memos/{mid}")
 assert resp2.status_code == 404


def test_delete_missing_returns_404(client):
 resp = client.delete("/api/memos/99999")
 assert resp.status_code == 404


def test_patch_updates_text(client):
 mid = _seed_memo(client)
 resp = client.patch(f"/api/memos/{mid}", json={"memo_text": "updated"})
 assert resp.status_code == 200
 assert resp.json()["memo"]["memo_text"] == "updated"


def test_patch_rejects_over_500(client):
 mid = _seed_memo(client)
 resp = client.patch(f"/api/memos/{mid}", json={"memo_text": "x" * 501})
 assert resp.status_code == 422
```

- [ ] **Step 6: DELETE 라우터 추가**

`backend/app/api/memo.py` 말미에 추가:

```python
@router.delete("/api/memos/{memo_id}")
def delete_memo(memo_id: int, request: Request):
 engine = request.app.state.engine
 ok = memo_service.delete_memo(engine, memo_id)
 if not ok:
 raise HTTPException(status_code=404, detail="memo not found")
 return {"ok": True}
```

- [ ] **Step 7: DELETE 테스트 통과**

```bash
uv run pytest tests/test_memo_endpoint_delete.py -v 2>&1 | tail -10
```

Expected: 4 passed.

- [ ] **Step 8: 전체 테스트**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 139 passed (130 + 5 + 4).

- [ ] **Step 9: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/memo.py backend/tests/test_memo_endpoint_list.py backend/tests/test_memo_endpoint_delete.py
git commit -m "$(cat <<'EOF'
feat(memo): add GET /api/memos, /api/jobs/{id}/memos, DELETE /api/memos/{id}

스펙 §4.1의 나머지 엔드포인트:
- GET /api/memos?limit=N: 전역 리스트 (job_alive 포함)
- GET /api/jobs/{id}/memos: 특정 Job 메모 (경량, segment UI용)
- DELETE /api/memos/{id}: 개별 삭제
- PATCH /api/memos/{id}: memo_text 500자 제한 검증
EOF
)"
```

---

### Task 2.4: Job 삭제 cascade

**Files:**
- Modify: `backend/app/services/jobs.py` (`delete_job` 내에서 memo cascade)
- Create: `backend/tests/test_job_delete_cascades_memos.py`

- [ ] **Step 1: 현재 delete_job 확인**

```bash
grep -n "def delete_job" backend/app/services/jobs.py
```

- [ ] **Step 2: cascade 테스트 작성**

Write `backend/tests/test_job_delete_cascades_memos.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.services.jobs import delete_job
from app.services.memo import list_memos_for_job


@pytest.fixture
def engine(tmp_path):
 db_path = tmp_path / "jobs.db"
 eng = create_db_engine(f"sqlite:///{db_path}")
 init_db(eng)
 return eng


@pytest.fixture
def settings(tmp_path):
 return Settings(
 database_url=f"sqlite:///{tmp_path / 'jobs.db'}",
 media_dir=tmp_path / "media",
 model_cache_dir=tmp_path / "models",
 )


def _seed_job_with_memos(engine, job_id="job1"):
 job = Job(
 id=job_id,
 source_url="https://e/1",
 source_kind=SourceKind.url.value,
 model_name="small",
 status=JobStatus.ready,
 title="T",
 expires_at=datetime.now(UTC) + timedelta(hours=24),
 )
 with Session(engine) as session:
 session.add(job)
 for i in range(3):
 session.add(Memo(
 job_id=job_id, segment_idx=i,
 memo_text=f"note {i}",
 segment_text_snapshot=f"s{i}",
 segment_start=float(i), segment_end=float(i) + 1,
 ))
 session.commit()


def test_delete_job_cascades_memos(engine, settings):
 _seed_job_with_memos(engine)
 _seed_job_with_memos(engine, job_id="job2")

 ok = delete_job(engine, settings, "job1")
 assert ok is True
 assert list_memos_for_job(engine, "job1") == []
 # 다른 Job의 메모는 보존
 assert len(list_memos_for_job(engine, "job2")) == 3


def test_delete_missing_job_does_not_raise(engine, settings):
 ok = delete_job(engine, settings, "nonexistent")
 assert ok is False
```

- [ ] **Step 3: 실행 → 두 번째 테스트만 통과 (첫 번째는 cascade 안 되므로 실패)**

```bash
uv run pytest tests/test_job_delete_cascades_memos.py -v 2>&1 | tail -10
```

Expected: `test_delete_job_cascades_memos` 실패 — memo가 남아있음.

- [ ] **Step 4: `services/jobs.py` 수정**

Read `backend/app/services/jobs.py`, `delete_job` 함수 찾아 수정:

```python
# 상단 import에 추가:
from app.services.memo import delete_memos_for_job as _delete_memos_for_job

# delete_job 함수 내부에 memo cascade 추가. 기존 함수:
def delete_job(engine: Engine, settings: Settings, job_id: str) -> bool:
 with Session(engine) as session:
 job = session.get(Job, job_id)
 if job is None:
 return False
 session.delete(job)
 session.commit()
 job_dir = settings.media_dir / job_id
 if job_dir.exists():
 shutil.rmtree(job_dir, ignore_errors=True)
 return True

# 위를 다음으로 교체:
def delete_job(engine: Engine, settings: Settings, job_id: str) -> bool:
 with Session(engine) as session:
 job = session.get(Job, job_id)
 if job is None:
 return False
 session.delete(job)
 session.commit()

 # Memo cascade (Job 삭제 후에 — FK 없으므로 순서는 무관하지만 명확성을 위해 뒤)
 _delete_memos_for_job(engine, job_id)

 job_dir = settings.media_dir / job_id
 if job_dir.exists():
 shutil.rmtree(job_dir, ignore_errors=True)
 return True
```

- [ ] **Step 5: 테스트 통과**

```bash
uv run pytest tests/test_job_delete_cascades_memos.py -v 2>&1 | tail -10
```

Expected: 2 passed.

- [ ] **Step 6: 기존 job 삭제 테스트 회귀**

```bash
uv run pytest tests/test_jobs_lifecycle.py -v 2>&1 | tail -10
```

Expected: 전부 pass.

- [ ] **Step 7: 전체**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 141 passed (139 + 2).

- [ ] **Step 8: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/jobs.py backend/tests/test_job_delete_cascades_memos.py
git commit -m "$(cat <<'EOF'
feat(memo): cascade delete memos when job is deleted

services.jobs.delete_job가 삭제 후 delete_memos_for_job 호출.
FK 없이 서비스 레이어에서 참조 무결성 유지.

스펙 §4.5: Job 명시 삭제 시 연결된 Memo도 함께 삭제.
프론트는 확인 다이얼로그에서 메모 개수 경고 (Phase 5).
EOF
)"
```

---

### Phase 2 완료 검증

- [ ] **Step 1: 전체 pytest + ruff**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
uv run ruff check app/ tests/ 2>&1 | tail -5
```

Expected: 141 passed. ruff 통과 또는 기존 수준 warnings only.

- [ ] **Step 2: 수동 API 호출로 계약 최종 점검 (옵션)**

```bash
cd /Users/loki/GenSub
docker compose up -d 2>&1 | tail -3
```

API가 뜨면:
```bash
curl -sS http://localhost:8000/api/memos | python3 -m json.tool
docker compose down
```

Expected: `{"items": []}` (실제 data가 있다면 아이템 리스트).

- [ ] **Step 3: 커밋 현황**

```bash
cd /Users/loki/GenSub
git log --oneline feature/memo ^master | cat
```

Expected: 7개 커밋 (Phase 1의 4개 + Phase 2의 3개 = schemas/POST/GET·DELETE/cascade).

Phase 2 완료.
