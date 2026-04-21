# Phase 1 — Backend: Memo 모델 + 서비스 레이어

목표: `memo` 테이블·모델·서비스 CRUD 함수를 TDD로 구현. API는 Phase 2에서.

**전제**: 기존 `master` 브랜치에서 시작, pytest 95 passed.

---

### Task 1.1: 브랜치 생성 + 기준선 확인

**Files:** (no file changes)

- [ ] **Step 1: 브랜치 생성**

```bash
cd /Users/loki/GenSub
git checkout master
git log --oneline -1
git checkout -b feature/memo
git branch --show-current
```

Expected: `feature/memo`.

- [ ] **Step 2: 기준선 pytest**

```bash
cd backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: `95 passed`.

---

### Task 1.2: Memo 모델 작성 + 단위 테스트

**Files:**
- Create: `backend/app/models/memo.py`
- Create: `backend/tests/test_memo_model.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 기존 `models/__init__.py` 확인**

```bash
cat backend/app/models/__init__.py
```

다른 모델 export 패턴 확인.

- [ ] **Step 2: 실패할 테스트 작성**

Write `backend/tests/test_memo_model.py`:

```python
import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.memo import Memo


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def test_memo_creation_and_persistence(engine):
    memo = Memo(
        job_id="job1",
        segment_idx=0,
        memo_text="test note",
        segment_text_snapshot="hello",
        segment_start=0.0,
        segment_end=1.5,
        job_title_snapshot="Test Video",
    )
    with Session(engine) as session:
        session.add(memo)
        session.commit()
        session.refresh(memo)
        assert memo.id is not None
        assert memo.created_at is not None
        assert memo.updated_at is not None


def test_memo_default_empty_text(engine):
    memo = Memo(
        job_id="job1",
        segment_idx=0,
        segment_text_snapshot="hello",
        segment_start=0.0,
        segment_end=1.5,
    )
    with Session(engine) as session:
        session.add(memo)
        session.commit()
        session.refresh(memo)
        assert memo.memo_text == ""


def test_memo_unique_constraint_on_job_segment(engine):
    from sqlalchemy.exc import IntegrityError

    with Session(engine) as session:
        session.add(Memo(
            job_id="job1", segment_idx=5,
            segment_text_snapshot="a", segment_start=0, segment_end=1,
        ))
        session.commit()

    with Session(engine) as session:
        session.add(Memo(
            job_id="job1", segment_idx=5,
            segment_text_snapshot="b", segment_start=0, segment_end=1,
        ))
        with pytest.raises(IntegrityError):
            session.commit()


def test_memo_allows_same_segment_idx_across_jobs(engine):
    with Session(engine) as session:
        session.add(Memo(
            job_id="job1", segment_idx=0,
            segment_text_snapshot="a", segment_start=0, segment_end=1,
        ))
        session.add(Memo(
            job_id="job2", segment_idx=0,
            segment_text_snapshot="b", segment_start=0, segment_end=1,
        ))
        session.commit()
```

- [ ] **Step 3: 실행 → 실패 확인**

```bash
cd /Users/loki/GenSub/backend
uv run pytest tests/test_memo_model.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError: No module named 'app.models.memo'`.

- [ ] **Step 4: 모델 구현**

Write `backend/app/models/memo.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Memo(SQLModel, table=True):
    __tablename__ = "memo"
    __table_args__ = (
        UniqueConstraint("job_id", "segment_idx", name="uq_memo_job_segment"),
    )

    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(index=True)
    segment_idx: int
    memo_text: str = Field(default="", max_length=500)

    segment_text_snapshot: str
    segment_start: float
    segment_end: float
    job_title_snapshot: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

- [ ] **Step 5: `models/__init__.py` export 추가**

Read `backend/app/models/__init__.py`. 기존 패턴을 따라 `from app.models.memo import Memo` 추가.

- [ ] **Step 6: 통과 확인**

```bash
uv run pytest tests/test_memo_model.py -v 2>&1 | tail -10
```

Expected: 4 passed.

- [ ] **Step 7: 전체 테스트 회귀**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 99 passed.

- [ ] **Step 8: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/models/memo.py backend/app/models/__init__.py backend/tests/test_memo_model.py
git commit -m "$(cat <<'EOF'
feat(memo): add Memo SQLModel with unique job+segment constraint

새 memo 테이블. (job_id, segment_idx) UNIQUE로 동일 세그먼트 중복
저장 방지. 스냅샷 필드로 영상 만료 시에도 리스트에 텍스트 보존.

memo_text 기본값 ""로 메모 없이 저장 가능 (Q3-A).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.3: Memo 서비스 — `toggle_save_memo` (핵심 로직)

**Files:**
- Create: `backend/app/services/memo.py`
- Create: `backend/tests/test_memo_service_toggle.py`

스펙 §4.2의 POST 토글 로직 + Job auto-pin.

- [ ] **Step 1: 기존 서비스 패턴 확인**

```bash
head -30 backend/app/services/jobs.py
```

Session 사용 패턴 재확인.

- [ ] **Step 2: 실패할 테스트 작성**

Write `backend/tests/test_memo_service_toggle.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.memo import toggle_save_memo


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


@pytest.fixture
def job_with_segment(engine):
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
    return job


def test_toggle_creates_memo_when_absent(engine, job_with_segment):
    result = toggle_save_memo(engine, "job1", 3)
    assert result.action == "created"
    assert result.memo is not None
    assert result.memo.memo_text == ""
    assert result.memo.segment_text_snapshot == "Hello world"
    assert result.memo.segment_start == 10.0
    assert result.memo.segment_end == 12.5
    assert result.memo.job_title_snapshot == "Test"


def test_toggle_auto_pins_job_on_create(engine, job_with_segment):
    toggle_save_memo(engine, "job1", 3)
    with Session(engine) as session:
        job = session.get(Job, "job1")
        assert job.pinned is True


def test_toggle_deletes_memo_when_empty_text(engine, job_with_segment):
    toggle_save_memo(engine, "job1", 3)
    result = toggle_save_memo(engine, "job1", 3)
    assert result.action == "deleted"
    assert result.memo is None

    with Session(engine) as session:
        count = session.query(Memo).filter(Memo.job_id == "job1").count()
        assert count == 0


def test_toggle_conflict_when_memo_has_text(engine, job_with_segment):
    first = toggle_save_memo(engine, "job1", 3)
    with Session(engine) as session:
        m = session.get(Memo, first.memo.id)
        m.memo_text = "some note"
        session.add(m)
        session.commit()

    result = toggle_save_memo(engine, "job1", 3)
    assert result.action == "conflict"
    assert result.memo is not None
    assert result.memo.memo_text == "some note"


def test_toggle_raises_when_segment_missing(engine, job_with_segment):
    with pytest.raises(LookupError):
        toggle_save_memo(engine, "job1", 999)


def test_toggle_raises_when_job_missing(engine):
    with pytest.raises(LookupError):
        toggle_save_memo(engine, "nonexistent", 0)
```

- [ ] **Step 3: 실행 → 실패**

```bash
uv run pytest tests/test_memo_service_toggle.py -v 2>&1 | tail -15
```

Expected: `ModuleNotFoundError: No module named 'app.services.memo'`.

- [ ] **Step 4: 서비스 구현**

Write `backend/app/services/memo.py`:

```python
"""Memo CRUD 서비스. Session 생명주기를 소유한다."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models.job import Job
from app.models.memo import Memo
from app.models.segment import Segment


@dataclass
class ToggleResult:
    action: Literal["created", "deleted", "conflict"]
    memo: Memo | None


def toggle_save_memo(engine: Engine, job_id: str, segment_idx: int) -> ToggleResult:
    """스펙 §4.2 POST 토글 로직.

    - 메모 없음 → 생성 (memo_text=""), Job auto-pin
    - 메모 있음 + memo_text 빈 문자열 → 삭제
    - 메모 있음 + memo_text 내용 있음 → conflict

    Raises:
        LookupError: Job 또는 Segment가 존재하지 않음.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job is None:
            raise LookupError(f"job not found: {job_id}")

        seg_stmt = select(Segment).where(
            Segment.job_id == job_id, Segment.idx == segment_idx
        )
        seg_result = session.exec(seg_stmt)
        segment = seg_result.first()
        if segment is None:
            raise LookupError(f"segment not found: {job_id}/{segment_idx}")

        memo_stmt = select(Memo).where(
            Memo.job_id == job_id, Memo.segment_idx == segment_idx
        )
        memo_result = session.exec(memo_stmt)
        existing = memo_result.first()

        if existing is not None:
            if existing.memo_text == "":
                session.delete(existing)
                session.commit()
                return ToggleResult(action="deleted", memo=None)
            return ToggleResult(action="conflict", memo=existing)

        memo = Memo(
            job_id=job_id,
            segment_idx=segment_idx,
            memo_text="",
            segment_text_snapshot=segment.text,
            segment_start=segment.start,
            segment_end=segment.end,
            job_title_snapshot=job.title,
        )
        session.add(memo)

        if not job.pinned:
            job.pinned = True
            job.updated_at = datetime.now(UTC)
            session.add(job)

        session.commit()
        session.refresh(memo)
        return ToggleResult(action="created", memo=memo)
```

- [ ] **Step 5: 통과 확인**

```bash
uv run pytest tests/test_memo_service_toggle.py -v 2>&1 | tail -15
```

Expected: 6 passed.

- [ ] **Step 6: 전체 테스트**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 105 passed.

- [ ] **Step 7: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/memo.py backend/tests/test_memo_service_toggle.py
git commit -m "$(cat <<'EOF'
feat(memo): toggle_save_memo service (create/delete/conflict)

스펙 §4.2 POST 토글:
- 메모 없음 → 생성 + Job auto-pin (Q4-A)
- 메모 있음 + 빈 텍스트 → 삭제 (toggle off)
- 메모 있음 + 내용 있음 → conflict (프론트가 확인 후 명시적 DELETE)

ToggleResult dataclass로 action 분기.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.4: Memo 서비스 — CRUD 보조 함수

**Files:**
- Modify: `backend/app/services/memo.py`
- Create: `backend/tests/test_memo_service_crud.py`

- [ ] **Step 1: 테스트 작성**

Write `backend/tests/test_memo_service_crud.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.memo import (
    delete_memo,
    delete_memos_for_job,
    get_memo_by_segment,
    list_memos_for_job,
    update_memo_text,
)


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def _seed(engine, job_id="job1", segment_idxs=(0,), job_title="Test"):
    job = Job(
        id=job_id,
        source_url=f"https://e/{job_id}",
        source_kind=SourceKind.url.value,
        model_name="small",
        status=JobStatus.ready,
        title=job_title,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    with Session(engine) as session:
        session.add(job)
        for idx in segment_idxs:
            session.add(Segment(
                job_id=job_id, idx=idx,
                start=float(idx), end=float(idx) + 1.0,
                text=f"text {idx}",
            ))
        session.commit()


def _make_memo(engine, job_id: str, segment_idx: int, memo_text: str = "") -> Memo:
    with Session(engine) as session:
        memo = Memo(
            job_id=job_id, segment_idx=segment_idx,
            memo_text=memo_text,
            segment_text_snapshot=f"text {segment_idx}",
            segment_start=float(segment_idx),
            segment_end=float(segment_idx) + 1.0,
            job_title_snapshot="Test",
        )
        session.add(memo)
        session.commit()
        session.refresh(memo)
        return memo


def test_get_memo_by_segment_returns_memo(engine):
    _seed(engine)
    m = _make_memo(engine, "job1", 0)
    got = get_memo_by_segment(engine, "job1", 0)
    assert got is not None
    assert got.id == m.id


def test_get_memo_by_segment_returns_none_when_missing(engine):
    _seed(engine)
    assert get_memo_by_segment(engine, "job1", 0) is None


def test_list_memos_for_job_returns_all(engine):
    _seed(engine, segment_idxs=(0, 1, 2))
    _make_memo(engine, "job1", 0)
    _make_memo(engine, "job1", 2)
    _seed(engine, job_id="job2")
    _make_memo(engine, "job2", 0)

    memos = list_memos_for_job(engine, "job1")
    assert len(memos) == 2
    idxs = {m.segment_idx for m in memos}
    assert idxs == {0, 2}


def test_update_memo_text_persists(engine):
    _seed(engine)
    m = _make_memo(engine, "job1", 0)
    updated = update_memo_text(engine, m.id, "new note")
    assert updated is not None
    assert updated.memo_text == "new note"
    assert updated.updated_at >= m.updated_at


def test_update_memo_text_missing_returns_none(engine):
    assert update_memo_text(engine, 99999, "any") is None


def test_delete_memo_removes_row(engine):
    _seed(engine)
    m = _make_memo(engine, "job1", 0)
    ok = delete_memo(engine, m.id)
    assert ok is True
    assert get_memo_by_segment(engine, "job1", 0) is None


def test_delete_memo_missing_returns_false(engine):
    assert delete_memo(engine, 99999) is False


def test_delete_memos_for_job_removes_all_for_job(engine):
    _seed(engine, segment_idxs=(0, 1))
    _make_memo(engine, "job1", 0)
    _make_memo(engine, "job1", 1)
    _seed(engine, job_id="job2")
    _make_memo(engine, "job2", 0)

    n = delete_memos_for_job(engine, "job1")
    assert n == 2
    assert list_memos_for_job(engine, "job1") == []
    assert len(list_memos_for_job(engine, "job2")) == 1
```

- [ ] **Step 2: 실패 확인**

```bash
uv run pytest tests/test_memo_service_crud.py -v 2>&1 | tail -10
```

- [ ] **Step 3: 서비스에 함수 추가**

`backend/app/services/memo.py` 말미에 추가:

```python
def get_memo_by_segment(engine: Engine, job_id: str, segment_idx: int) -> Memo | None:
    with Session(engine) as session:
        stmt = select(Memo).where(
            Memo.job_id == job_id, Memo.segment_idx == segment_idx
        )
        result = session.exec(stmt)
        return result.first()


def list_memos_for_job(engine: Engine, job_id: str) -> list[Memo]:
    with Session(engine) as session:
        stmt = (
            select(Memo)
            .where(Memo.job_id == job_id)
            .order_by(Memo.segment_idx)
        )
        result = session.exec(stmt)
        return list(result.all())


def update_memo_text(engine: Engine, memo_id: int, memo_text: str) -> Memo | None:
    with Session(engine) as session:
        memo = session.get(Memo, memo_id)
        if memo is None:
            return None
        memo.memo_text = memo_text
        memo.updated_at = datetime.now(UTC)
        session.add(memo)
        session.commit()
        session.refresh(memo)
        return memo


def delete_memo(engine: Engine, memo_id: int) -> bool:
    with Session(engine) as session:
        memo = session.get(Memo, memo_id)
        if memo is None:
            return False
        session.delete(memo)
        session.commit()
        return True


def delete_memos_for_job(engine: Engine, job_id: str) -> int:
    """Job 삭제와 함께 호출. 제거된 메모 개수 반환."""
    with Session(engine) as session:
        stmt = select(Memo).where(Memo.job_id == job_id)
        result = session.exec(stmt)
        memos = list(result.all())
        for m in memos:
            session.delete(m)
        session.commit()
        return len(memos)
```

- [ ] **Step 4: 통과**

```bash
uv run pytest tests/test_memo_service_crud.py -v 2>&1 | tail -10
```

Expected: 8 passed.

- [ ] **Step 5: 전체**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 113 passed.

- [ ] **Step 6: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/memo.py backend/tests/test_memo_service_crud.py
git commit -m "$(cat <<'EOF'
feat(memo): add get/list/update/delete service functions

- get_memo_by_segment: 세그먼트 UI 저장 상태 표시용
- list_memos_for_job: 특정 Job 메모 (segment_idx 오름차순)
- update_memo_text: 메모 수정 (updated_at 갱신)
- delete_memo: 개별 삭제
- delete_memos_for_job: Phase 2의 Job 삭제 cascade용

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.5: Memo 서비스 — 전역 리스트 (`list_all_memos_with_liveness`)

**Files:**
- Modify: `backend/app/services/memo.py`
- Create: `backend/tests/test_memo_service_global.py`

스펙 §4.3의 `/api/memos` 응답 구성용. Job/Segment LEFT JOIN 한 번으로 `job_alive` + 현재값/스냅샷 merge.

- [ ] **Step 1: 테스트 작성**

Write `backend/tests/test_memo_service_global.py`:

```python
from dataclasses import is_dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus, SourceKind
from app.models.memo import Memo
from app.models.segment import Segment
from app.services.memo import MemoView, list_all_memos_with_liveness


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "jobs.db"
    eng = create_db_engine(f"sqlite:///{db_path}")
    init_db(eng)
    return eng


def _insert_job(engine, job_id: str, title: str):
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


def _insert_segment(engine, job_id: str, idx: int, text: str):
    with Session(engine) as session:
        session.add(Segment(
            job_id=job_id, idx=idx,
            start=float(idx), end=float(idx) + 1,
            text=text,
        ))
        session.commit()


def _insert_memo(engine, job_id: str, idx: int, snap_text: str, snap_title: str, memo_text: str = "") -> int:
    with Session(engine) as session:
        m = Memo(
            job_id=job_id, segment_idx=idx,
            memo_text=memo_text,
            segment_text_snapshot=snap_text,
            segment_start=float(idx), segment_end=float(idx) + 1,
            job_title_snapshot=snap_title,
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        return m.id


def test_memo_view_is_dataclass():
    assert is_dataclass(MemoView)


def test_list_returns_empty_when_no_memos(engine):
    assert list_all_memos_with_liveness(engine) == []


def test_list_newest_first(engine):
    _insert_job(engine, "job1", "T")
    _insert_segment(engine, "job1", 0, "a")
    _insert_segment(engine, "job1", 1, "b")
    id_a = _insert_memo(engine, "job1", 0, "a", "T")
    import time
    time.sleep(0.01)
    id_b = _insert_memo(engine, "job1", 1, "b", "T")

    items = list_all_memos_with_liveness(engine)
    assert [x.id for x in items] == [id_b, id_a]


def test_list_job_alive_true_when_exists(engine):
    _insert_job(engine, "job1", "T")
    _insert_segment(engine, "job1", 0, "cur")
    _insert_memo(engine, "job1", 0, "snap", "T")

    items = list_all_memos_with_liveness(engine)
    assert len(items) == 1
    assert items[0].job_alive is True


def test_list_uses_current_text_when_available(engine):
    _insert_job(engine, "job1", "Current Title")
    _insert_segment(engine, "job1", 0, "current text")
    _insert_memo(engine, "job1", 0, snap_text="snapshot text", snap_title="Snapshot Title")

    items = list_all_memos_with_liveness(engine)
    assert len(items) == 1
    assert items[0].segment_text == "current text"
    assert items[0].job_title == "Current Title"


def test_list_falls_back_to_snapshot_when_job_missing(engine):
    _insert_memo(engine, "orphan_job", 0, "snap", "snap_title")

    items = list_all_memos_with_liveness(engine)
    assert len(items) == 1
    assert items[0].job_alive is False
    assert items[0].segment_text == "snap"
    assert items[0].job_title == "snap_title"


def test_list_respects_limit(engine):
    _insert_job(engine, "job1", "T")
    for i in range(5):
        _insert_segment(engine, "job1", i, f"s{i}")
        _insert_memo(engine, "job1", i, f"s{i}", "T")

    items = list_all_memos_with_liveness(engine, limit=3)
    assert len(items) == 3
```

- [ ] **Step 2: 실패 확인**

```bash
uv run pytest tests/test_memo_service_global.py -v 2>&1 | tail -10
```

- [ ] **Step 3: 구현**

`backend/app/services/memo.py` 말미에 추가:

```python
@dataclass
class MemoView:
    """전역 리스트 응답의 한 항목."""
    id: int
    job_id: str
    segment_idx: int
    memo_text: str
    segment_text: str
    start: float
    end: float
    job_title: str | None
    job_alive: bool
    created_at: datetime
    updated_at: datetime


def list_all_memos_with_liveness(engine: Engine, limit: int = 100) -> list[MemoView]:
    """전역 메모 리스트. Job/Segment LEFT JOIN 으로 N+1 방지.

    Job/Segment가 살아있으면 현재값, 없으면 스냅샷으로 채운다.
    """
    with Session(engine) as session:
        stmt = (
            select(Memo, Job, Segment)
            .join(Job, Job.id == Memo.job_id, isouter=True)
            .join(
                Segment,
                (Segment.job_id == Memo.job_id) & (Segment.idx == Memo.segment_idx),
                isouter=True,
            )
            .order_by(Memo.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        result = session.exec(stmt)
        rows = list(result.all())

    items: list[MemoView] = []
    for memo, job, segment in rows:
        items.append(MemoView(
            id=memo.id,
            job_id=memo.job_id,
            segment_idx=memo.segment_idx,
            memo_text=memo.memo_text,
            segment_text=(segment.text if segment else memo.segment_text_snapshot),
            start=memo.segment_start,
            end=memo.segment_end,
            job_title=(job.title if job else memo.job_title_snapshot),
            job_alive=(job is not None),
            created_at=memo.created_at,
            updated_at=memo.updated_at,
        ))
    return items
```

- [ ] **Step 4: 통과**

```bash
uv run pytest tests/test_memo_service_global.py -v 2>&1 | tail -10
```

Expected: 7 passed.

- [ ] **Step 5: 전체**

```bash
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 120 passed.

- [ ] **Step 6: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/memo.py backend/tests/test_memo_service_global.py
git commit -m "$(cat <<'EOF'
feat(memo): list_all_memos_with_liveness for global list

스펙 §4.3 /api/memos 응답 구성:
- Memo × Job × Segment LEFT JOIN 한 번으로 N+1 회피
- job_alive는 LEFT JOIN의 Job NULL 여부
- segment_text/job_title은 현재값 우선, 없으면 스냅샷
- 최신순, limit 기본 100

MemoView dataclass로 API 응답 스키마와 분리.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Phase 1 완료 검증

- [ ] **Step 1: 전체 pytest**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 120 passed.

- [ ] **Step 2: 커밋 로그 확인**

```bash
cd /Users/loki/GenSub
git log --oneline feature/memo ^master | cat
```

Expected: 4개 커밋 (모델 / toggle / CRUD / global).

Phase 1 완료.
