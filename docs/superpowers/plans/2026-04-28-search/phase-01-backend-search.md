# Phase 1 — Backend: search 서비스 + API + 테스트

목표: SQLite LIKE 매치 기반의 통합 검색 서비스 + REST 엔드포인트를 TDD로 구현.

**전제**: master 브랜치, pytest 142 passed.

---

### Task 1.1: feature/search 브랜치 생성 + 기준선

**Files:** (no file changes)

- [ ] **Step 1: 브랜치 생성**

```bash
cd /Users/loki/GenSub
git checkout master
git log --oneline -1
git checkout -b feature/search
git branch --show-current
```

Expected: `feature/search`

- [ ] **Step 2: 기준선 pytest**

```bash
cd backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: `142 passed`

---

### Task 1.2: SearchHit dataclass + search_all 서비스 (TDD)

**Files:**
- Create: `backend/app/services/search.py`
- Create: `backend/tests/test_search_service.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_search_service.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.search import SearchHit, search_all


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def test_empty_query_returns_empty_list(engine):
    assert search_all(engine, "") == []
    assert search_all(engine, "   ") == []


def _make_job(engine, jid: str, title: str):
    job = Job(
        id=jid,
        source_url=f"https://e/{jid}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title=title,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()


def _make_segment(engine, jid: str, idx: int, text: str):
    with Session(engine) as session:
        session.add(Segment(
            job_id=jid, idx=idx,
            start=float(idx), end=float(idx) + 1,
            text=text,
        ))
        session.commit()


def _make_memo(engine, jid: str, idx: int, memo_text: str, snap_text: str):
    with Session(engine) as session:
        m = Memo(
            job_id=jid, segment_idx=idx,
            memo_text=memo_text,
            segment_text_snapshot=snap_text,
            segment_start=float(idx), segment_end=float(idx) + 1,
            job_title_snapshot="t",
        )
        session.add(m)
        session.commit()


def test_matches_segment_text(engine):
    _make_job(engine, "j1", "Test Video")
    _make_segment(engine, "j1", 0, "Hello world")
    _make_segment(engine, "j1", 1, "Goodbye sky")

    hits = search_all(engine, "Hello")
    assert len(hits) == 1
    assert hits[0].kind == "segment"
    assert hits[0].segment_text == "Hello world"
    assert hits[0].segment_idx == 0
    assert hits[0].job_id == "j1"
    assert hits[0].job_title == "Test Video"


def test_matches_memo_text(engine):
    _make_job(engine, "j1", "T")
    _make_segment(engine, "j1", 0, "abc")
    _make_memo(engine, "j1", 0, memo_text="중요한 표현", snap_text="abc")

    hits = search_all(engine, "중요")
    assert len(hits) == 1
    assert hits[0].kind == "memo"
    assert hits[0].memo_text == "중요한 표현"


def test_matches_job_title(engine):
    _make_job(engine, "j1", "영화 추천 모음")
    _make_segment(engine, "j1", 0, "unrelated text")

    hits = search_all(engine, "영화")
    assert len(hits) == 1
    assert hits[0].kind == "job"
    assert hits[0].job_title == "영화 추천 모음"


def test_korean_substring(engine):
    _make_job(engine, "j1", "T")
    _make_segment(engine, "j1", 0, "안녕하세요 반갑습니다")

    hits = search_all(engine, "안녕")
    assert len(hits) == 1
    assert hits[0].kind == "segment"


def test_case_insensitive_ascii(engine):
    _make_job(engine, "j1", "T")
    _make_segment(engine, "j1", 0, "Hello World")

    hits = search_all(engine, "hello")
    assert len(hits) == 1


def test_respects_limit(engine):
    _make_job(engine, "j1", "T")
    for i in range(10):
        _make_segment(engine, "j1", i, f"hello {i}")

    hits = search_all(engine, "hello", limit=3)
    assert len(hits) == 3


def test_excludes_orphan_segments(engine):
    """Job 없는 segment는 결과에서 제외 (defensive INNER JOIN)."""
    with Session(engine) as session:
        session.add(Segment(
            job_id="ghost", idx=0,
            start=0, end=1,
            text="hello orphan",
        ))
        session.commit()

    hits = search_all(engine, "hello")
    assert hits == []


def test_groups_results_in_order_job_memo_segment(engine):
    _make_job(engine, "j1", "Search me")
    _make_segment(engine, "j1", 0, "search me too")
    _make_memo(engine, "j1", 0, memo_text="search me note", snap_text="search me too")

    hits = search_all(engine, "search me")
    kinds = [h.kind for h in hits]
    assert kinds == ["job", "memo", "segment"]
```

- [ ] **Step 2: 실행 → 실패 확인**

```bash
cd /Users/loki/GenSub/backend
uv run pytest tests/test_search_service.py -v 2>&1 | tail -15
```

Expected: ModuleNotFoundError: 'app.services.search'

- [ ] **Step 3: 서비스 구현**

Write `backend/app/services/search.py`:

```python
"""검색 서비스. 자막·메모·영상 제목을 LIKE 부분 매치로 검색."""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models.job import Job
from app.models.memo import Memo
from app.models.segment import Segment


@dataclass
class SearchHit:
    kind: Literal["job", "memo", "segment"]
    job_id: str
    job_title: str | None
    segment_idx: int | None = None
    segment_text: str | None = None
    start: float | None = None
    end: float | None = None
    memo_id: int | None = None
    memo_text: str | None = None


def search_all(engine: Engine, query: str, limit: int = 50) -> list[SearchHit]:
    """자막 + 메모 + 영상 제목을 query로 부분 매치 검색.

    - 빈 query → 즉시 빈 리스트.
    - 결과 순서: job → memo → segment, 각 그룹 내 updated_at desc.
    - INNER JOIN 으로 orphan segment/memo 자동 제외.
    - SQLite ilike 는 ASCII 에서 case-insensitive (한국어는 본래 case 없음).
    """
    q = (query or "").strip()
    if not q:
        return []

    pattern = f"%{q}%"
    hits: list[SearchHit] = []

    with Session(engine) as session:
        # 1) Job titles
        job_stmt = (
            select(Job)
            .where(Job.title.ilike(pattern))
            .order_by(Job.updated_at.desc())
            .limit(limit)
        )
        job_result = session.exec(job_stmt)
        for job in job_result.all():
            hits.append(SearchHit(
                kind="job",
                job_id=job.id,
                job_title=job.title,
            ))

        # 2) Memos (memo_text or snapshot text)
        memo_stmt = (
            select(Memo, Job)
            .join(Job, Job.id == Memo.job_id)
            .where(
                (Memo.memo_text.ilike(pattern))
                | (Memo.segment_text_snapshot.ilike(pattern))
            )
            .order_by(Memo.updated_at.desc())
            .limit(limit)
        )
        memo_result = session.exec(memo_stmt)
        for memo, job in memo_result.all():
            hits.append(SearchHit(
                kind="memo",
                job_id=memo.job_id,
                job_title=job.title,
                memo_id=memo.id,
                memo_text=memo.memo_text,
                segment_idx=memo.segment_idx,
                segment_text=memo.segment_text_snapshot,
                start=memo.segment_start,
                end=memo.segment_end,
            ))

        # 3) Segments (live jobs only)
        seg_stmt = (
            select(Segment, Job)
            .join(Job, Job.id == Segment.job_id)
            .where(Segment.text.ilike(pattern))
            .order_by(Job.updated_at.desc(), Segment.idx)
            .limit(limit)
        )
        seg_result = session.exec(seg_stmt)
        for seg, job in seg_result.all():
            hits.append(SearchHit(
                kind="segment",
                job_id=seg.job_id,
                job_title=job.title,
                segment_idx=seg.idx,
                segment_text=seg.text,
                start=seg.start,
                end=seg.end,
            ))

    return hits[:limit]
```

note: type-checker 가 SQLModel column attribute (`Job.title.ilike` 등) 를 동적이라 인식 못 할 수도 있음. mypy 가 시끄럽게 굴면 `# type: ignore[union-attr]` 를 끝에 붙여라.

- [ ] **Step 4: 실행 → 통과**

```bash
uv run pytest tests/test_search_service.py -v 2>&1 | tail -15
```

Expected: 9 passed.

- [ ] **Step 5: 전체 회귀**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 151 passed (142 + 9).

- [ ] **Step 6: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/search.py backend/tests/test_search_service.py
git commit -m "feat(search): add search_all service with LIKE substring matching

자막 (Segment.text) + 메모 (Memo.memo_text/segment_text_snapshot) +
영상 제목 (Job.title) 을 부분 매치 검색.

- 빈 query는 즉시 빈 리스트 (DB hit 없음)
- 결과 순서: job → memo → segment, 각 그룹 내 updated_at desc
- INNER JOIN 으로 orphan segment/memo 자동 제외
- ilike 로 ASCII case-insensitive (한국어는 본래 case 없음)
- limit은 전체 합산 limit

테스트 9 케이스 (빈 query, 자막/메모/제목 매치, 한국어, 대소문자,
limit, orphan 제외, 그룹 순서)."
```

---

### Task 1.3: REST 엔드포인트 + 라우터 등록 (TDD)

**Files:**
- Create: `backend/app/api/search.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_search_endpoint.py`

- [ ] **Step 1: 통합 테스트 작성**

Write `backend/tests/test_search_endpoint.py`:

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


def _seed(client, jid="j1", title="Hello video"):
    engine = client.app.state.engine
    job = Job(
        id=jid,
        source_url=f"https://e/{jid}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title=title,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    seg = Segment(
        job_id=jid, idx=0,
        start=0, end=1,
        text="searchable segment text",
    )
    memo = Memo(
        job_id=jid, segment_idx=0,
        memo_text="searchable memo body",
        segment_text_snapshot="searchable segment text",
        segment_start=0, segment_end=1,
    )
    with Session(engine) as session:
        session.add(job)
        session.add(seg)
        session.add(memo)
        session.commit()


def test_get_search_empty_query(client):
    resp = client.get("/api/search?q=")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_get_search_returns_grouped_results(client):
    _seed(client)
    resp = client.get("/api/search?q=searchable")
    assert resp.status_code == 200
    items = resp.json()["items"]
    kinds = [i["kind"] for i in items]
    assert "memo" in kinds
    assert "segment" in kinds


def test_get_search_response_shape_segment(client):
    _seed(client)
    resp = client.get("/api/search?q=searchable")
    items = resp.json()["items"]
    seg_items = [i for i in items if i["kind"] == "segment"]
    assert len(seg_items) == 1
    s = seg_items[0]
    assert s["job_id"] == "j1"
    assert s["job_title"] == "Hello video"
    assert s["segment_idx"] == 0
    assert s["segment_text"] == "searchable segment text"
    assert "start" in s
    assert "end" in s


def test_get_search_response_shape_memo(client):
    _seed(client)
    resp = client.get("/api/search?q=searchable")
    items = resp.json()["items"]
    memo_items = [i for i in items if i["kind"] == "memo"]
    assert len(memo_items) == 1
    m = memo_items[0]
    assert m["job_id"] == "j1"
    assert m["memo_text"] == "searchable memo body"
    assert "memo_id" in m


def test_get_search_response_shape_job(client):
    _seed(client, title="Special title here")
    resp = client.get("/api/search?q=Special")
    items = resp.json()["items"]
    job_items = [i for i in items if i["kind"] == "job"]
    assert len(job_items) == 1
    j = job_items[0]
    assert j["job_id"] == "j1"
    assert j["job_title"] == "Special title here"


def test_get_search_limit_param(client):
    engine = client.app.state.engine
    job = Job(
        id="j1",
        source_url="https://e/j1",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title="T",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        for i in range(20):
            session.add(Segment(
                job_id="j1", idx=i,
                start=float(i), end=float(i) + 1,
                text=f"hello {i}",
            ))
        session.commit()

    resp = client.get("/api/search?q=hello&limit=5")
    items = resp.json()["items"]
    assert len(items) == 5
```

- [ ] **Step 2: 실행 → 실패**

```bash
uv run pytest tests/test_search_endpoint.py -v 2>&1 | tail -10
```

Expected: 404 또는 module 없음.

- [ ] **Step 3: 라우터 구현**

Write `backend/app/api/search.py`:

```python
from fastapi import APIRouter, Request

from app.services import search as search_service

router = APIRouter(tags=["search"])


def _hit_to_dict(hit) -> dict:
    """SearchHit dataclass → JSON-friendly dict (None 필드 제외)."""
    out: dict = {
        "kind": hit.kind,
        "job_id": hit.job_id,
        "job_title": hit.job_title,
    }
    if hit.segment_idx is not None:
        out["segment_idx"] = hit.segment_idx
    if hit.segment_text is not None:
        out["segment_text"] = hit.segment_text
    if hit.start is not None:
        out["start"] = hit.start
    if hit.end is not None:
        out["end"] = hit.end
    if hit.memo_id is not None:
        out["memo_id"] = hit.memo_id
    if hit.memo_text is not None:
        out["memo_text"] = hit.memo_text
    return out


@router.get("/api/search")
def search(request: Request, q: str = "", limit: int = 50) -> dict:
    hits = search_service.search_all(request.app.state.engine, q, limit=limit)
    return {"items": [_hit_to_dict(h) for h in hits]}
```

- [ ] **Step 4: main.py에 라우터 등록**

Read `backend/app/main.py`. import 블록에 추가:

```python
from app.api.search import router as search_router
```

`create_app()` 안의 router 등록 블록(다른 `include_router(...)` 줄 근처)에 추가:

```python
app.include_router(search_router)
```

- [ ] **Step 5: 통합 테스트 통과**

```bash
uv run pytest tests/test_search_endpoint.py -v 2>&1 | tail -15
```

Expected: 6 passed.

- [ ] **Step 6: 전체 회귀**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 157 passed (151 + 6).

- [ ] **Step 7: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/api/search.py backend/app/main.py backend/tests/test_search_endpoint.py
git commit -m "feat(search): add GET /api/search endpoint

스펙 §4.3:
- GET /api/search?q=<query>&limit=50
- 응답: {items: [{kind: 'job'|'memo'|'segment', ...}]}
- 빈 query → {items: []}
- None 필드는 응답에서 제외 (kind 별 채워진 필드만 노출)

통합 테스트 6 케이스 (빈 query / 결과 그룹핑 / 응답 shape × 3 / limit)."
```

---

### Phase 1 완료 검증

- [ ] **Step 1: 전체 pytest**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 157 passed.

- [ ] **Step 2: ruff 검사**

```bash
uv run ruff check app/services/search.py app/api/search.py 2>&1 | tail
```

Expected: 통과 또는 기존 수준 warnings.

- [ ] **Step 3: 커밋 로그**

```bash
cd /Users/loki/GenSub
git log --oneline feature/search ^master | cat
```

Expected: 2 커밋 (서비스 / 엔드포인트).

Phase 1 완료. Phase 2 진행.
