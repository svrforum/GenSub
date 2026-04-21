# 메모 기능 설계 명세

**날짜**: 2026-04-22
**프로젝트**: GenSub
**목적**: 사용자가 영상 자막 세그먼트를 **구간 단위로 저장**하고 선택적으로 **메모**를 붙여, **영상과 무관한 전역 메모 리스트**에서 열람·"보러가기"할 수 있게 한다.
**스펙 성격**: 신규 기능. 기존 스키마·UI 손대지 않고 덧붙이는 방식.

---

## 1. 배경과 동기

현재 GenSub은 영상 단위 북마크(`Job.pinned`)만 지원한다. 사용자는 영상의 특정 구간을 "좋다"고 느꼈을 때 나중에 다시 찾아갈 방법이 없다. 제안된 기능은 자막 세그먼트 단위의 북마크와 짧은 메모를 쌓아, 이를 영상 간 횡단 뷰로 조회하고 원본 영상·시점으로 즉시 돌아가는 것이다.

**Q1~Q4 브레인스토밍 결론** (2026-04-22):
- Q1 (용도) → **D**: 단순 북마크 + 메모 + 보러가기. 태그/검색/번역/내보내기 제외 (YAGNI).
- Q2 (사이드바 UI) → **A**: 탭 분리 (영상 / 메모), 카운트 배지.
- Q3 (저장 UX) → **A**: 📎 1클릭 즉시 저장, 메모는 선택적으로 나중에 인라인 입력.
- Q4 (Job 삭제/만료) → **A**: 메모 있으면 Job 자동 pin, Job 삭제 시 cascade (사용자 확인 다이얼로그 포함).

---

## 2. Goals / Non-Goals

### Goals
1. 세그먼트 단위로 북마크 + 짧은 메모 저장.
2. 영상과 무관한 전역 메모 리스트 조회.
3. 리스트에서 **"보러가기"** — 해당 영상 열고 해당 시점으로 seek.
4. 메모가 있는 영상은 자동 pin되어 TTL로 만료되지 않음.
5. 만에 하나 영상이 사라진 경우도 메모 텍스트는 스냅샷으로 남음.
6. 기존 `Job`·`Segment` 스키마 무변경, 기존 데이터 안전.

### Non-Goals
- 태그, 검색, 필터, 정렬 — 쌓인 메모 50개 이상이 되면 재논의.
- 메모 마크다운/리치 텍스트 — plain text로 충분.
- 메모 공유·내보내기 — 개인 스코프.
- 번역 자동 채움 — 언어 학습 전용 기능 아님(Q1-D).
- 모바일 최적화 — 현재 스코프 데스크톱 우선과 동일.

---

## 3. 데이터 모델

### 3.1 신규 테이블 `memo`

```python
# backend/app/models/memo.py
from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Memo(SQLModel, table=True):
    __tablename__ = "memo"
    __table_args__ = (UniqueConstraint("job_id", "segment_idx", name="uq_memo_job_segment"),)

    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(index=True)             # Job.id 참조. FK 없음 (스냅샷 기반 복원 허용).
    segment_idx: int
    memo_text: str = Field(default="", max_length=500)

    # 스냅샷 필드: Job/Segment가 사라져도 리스트에 남김.
    segment_text_snapshot: str
    segment_start: float
    segment_end: float
    job_title_snapshot: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

**주의**: SQLite는 SQL-level VARCHAR 길이를 강제하지 않는다. `max_length=500` 은 Pydantic 레벨 검증이므로, API 입력(`memo_text` body) 에 Pydantic 스키마로 같은 제약을 걸어 이중 방어한다.

**제약**:
- `UNIQUE(job_id, segment_idx)`: 같은 세그먼트에 두 번 저장 불가. 두 번째 호출은 toggle-off(삭제)로 처리.
- `memo_text` 기본값 `""`: 메모 없이 저장 가능.
- `memo_text.max_length=500`: 서버와 프론트 양쪽 검증.
- FK 없음: Job이 drop되거나 test에서 orphan 만들어도 Memo 존재는 스냅샷으로 의미 유지.

### 3.2 기존 테이블 무변경

- `Job`, `Segment` 컬럼 추가/삭제/변경 없음.
- `Job.pinned`는 기존대로 사용 (메모 있으면 서비스 레이어가 자동 true로 세팅).

### 3.3 마이그레이션 전략

- `init_db(engine)` 의 `SQLModel.metadata.create_all(engine)` 이 `memo` 테이블을 자동 생성한다. 기존 테이블 무영향.
- 신규 컨테이너 기동 시 `services/backup.py:backup_database()` 가 자동 DB 백업 (이미 작동 중 — R6).
- 롤백: 이전 이미지로 되돌려도 `memo` 테이블은 단순히 미사용 상태로 존재 — 데이터 손실 없음.

---

## 4. 서버 API

### 4.1 엔드포인트 일람

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/jobs/{job_id}/segments/{idx}/memo` | 메모 생성 또는 toggle-off |
| `GET` | `/api/memos?limit=100` | 전역 메모 리스트 (최신순, `job_alive` 포함) |
| `GET` | `/api/jobs/{job_id}/memos` | 특정 Job의 메모 리스트 (경량, segment 표시용) |
| `PATCH` | `/api/memos/{memo_id}` | `memo_text` 수정 |
| `DELETE` | `/api/memos/{memo_id}` | 개별 메모 삭제 |

### 4.2 POST 생성 동작 (toggle-save)

```
POST /api/jobs/{job_id}/segments/{idx}/memo
Body: (없음)
```

순수한 저장 토글. 메모 텍스트는 이 엔드포인트에서 설정하지 않고, 저장 후 `PATCH /api/memos/{id}` 로 별도 수정 (Q3-A 패턴).

동작:
1. `job_id` / `segment_idx` 유효성 확인. 해당 Segment 없으면 `404`.
2. 이미 메모가 있는가?
   - **없음**: 생성. Segment의 `text`·`start`·`end`·Job `title` 을 스냅샷으로 기록. `memo_text=""`. 응답 `201 {"ok": true, "action": "created", "memo": {...}}`.
   - **있음 + `memo_text`가 빈 문자열**: 삭제(toggle-off). 응답 `200 {"ok": true, "action": "deleted"}`.
   - **있음 + `memo_text`에 내용 있음**: `409 Conflict {"detail": "memo_has_text", "memo_id": <id>}`. 프론트가 확인 다이얼로그 후 `DELETE /api/memos/{id}` 로 명시적 삭제. **실수로 메모 내용을 잃는 것 방지**.
3. 생성 시 Job `pinned=true` 자동 세팅 (기존 `services.jobs.pin_job` 재사용; 이미 pinned면 no-op).

### 4.3 GET 전역 리스트 응답 포맷

```json
{
  "items": [
    {
      "id": 1,
      "job_id": "059ddd86…",
      "segment_idx": 12,
      "memo_text": "이 표현 좋네",
      "segment_text": "Movies coming out in 2026.",
      "start": 45.2,
      "end": 48.7,
      "job_title": "Why movies these days SUCK…",
      "job_alive": true,
      "created_at": "2026-04-22T10:00:00+00:00",
      "updated_at": "2026-04-22T10:05:00+00:00"
    }
  ]
}
```

`job_alive`는 서버에서 해당 `job_id` 존재 여부를 한 번 확인한 결과(`EXISTS` 서브쿼리 단일 round-trip). N+1 쿼리 피한다.

`segment_text` / `job_title` 은 **Job이 살아있을 땐 현재 값** 으로 갱신, **죽었을 땐 스냅샷**으로 fallback:
```python
# pseudo
segment_text = current_segment.text if current_segment else memo.segment_text_snapshot
job_title = current_job.title if current_job else memo.job_title_snapshot
```

### 4.4 PATCH / DELETE

```
PATCH /api/memos/{memo_id}   Body: {"memo_text": "..."}   → 응답: 수정된 memo
DELETE /api/memos/{memo_id}                               → 응답: {"ok": true}
```

### 4.5 Job 삭제와 cascade

`DELETE /api/jobs/{job_id}` (기존) 의 동작 확장:
- `services/memo.delete_memos_for_job(engine, job_id)` 을 `services.jobs.delete_job` 내부에서 호출 (Job 삭제 전에).
- 프론트의 확인 다이얼로그 문구 변경: `"이 영상의 메모 N개도 함께 삭제됩니다."` (메모가 있을 때만)

### 4.6 레이어 경계

- `api/memo.py` 라우터는 `services/memo.py` 만 호출. `Session` 직접 사용 금지.
- `services/memo.py` 가 Session 생명주기 소유 (기존 `services/jobs.py` 패턴 준수).

---

## 5. 프론트엔드 구조

### 5.1 사이드바 탭

`Sidebar.svelte` 상단에 탭 추가:

```
┌ [G] 새 자막              [⇤] ┐
├──────────────────────────────┤
│  ┌─────────┬─────────┐       │
│  │ 영상 2  │ 메모 5  │       │
│  └─────────┴─────────┘       │
├──────────────────────────────┤
│  (선택된 탭 내용)             │
├──────────────────────────────┤
│  작업은 24시간 후 자동 삭제… │
└──────────────────────────────┘
```

- 탭 상태: `let sidebarTab: 'videos' | 'memos' = 'videos'`
- 아이콘: 영상 = `Video`, 메모 = `Bookmark` (lucide-svelte)
- 카운트 배지: `$history.length` / `$memos.length`
- 기존 **영상 탭 내용은 그대로** (기존 코드 경로 보존 — 회귀 방지)

### 5.2 메모 탭 내용

```svelte
{#if $memos.length === 0}
  <EmptyState>
    아직 저장한 문장이 없어요.
    자막 세그먼트 오른쪽 📎 버튼으로 저장하면 여기에 모여요.
  </EmptyState>
{:else}
  <ul>
    {#each $memos as memo (memo.id)}
      <MemoCard {memo} onOpen={openMemo} onDelete={deleteMemo} />
    {/each}
  </ul>
{/if}
```

**`MemoCard.svelte`** 구성:
- 2행 ellipsis: `segment_text`
- 메모 텍스트 (`memo_text` 있으면)
- 메타: `{job_title} · {formatMMSS(start)}`
- `job_alive=false` 인 경우: 회색 톤 + "영상 삭제됨" 배지 + 클릭 비활성
- Hover 시 우측에 삭제 아이콘

카드 클릭 → `openMemo(memo)`:
```ts
current.set({
  screen: 'ready',
  jobId: memo.job_id,
  initialTime: memo.start,   // ← 신규
  job: null,
  progress: 1,
  stageMessage: '',
  errorMessage: null,
});
```

### 5.3 SegmentList 저장 버튼

`SegmentList.svelte` 내 각 세그먼트에 `SegmentMemo.svelte` 추가:

```
┌─────────────────────────────────────┐
│  ▶  0:45 → 0:48               📎    │  (미저장 — outline 아이콘)
│     Movies coming out in 2026.      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  ▶  0:45 → 0:48           📎(fill)  │  (저장됨 — 파란 fill)
│     Movies coming out in 2026.      │
│     💭 이 표현 좋네 [편집]          │  (저장 시에만 표시)
└─────────────────────────────────────┘
```

**`SegmentMemo.svelte`** 컴포넌트:
- Props: `jobId`, `segmentIdx`, `memo: MemoDto | null`
- 📎 클릭 → `jobId+idx` 로 POST → 서버에서 create/delete toggle → 스토어 갱신
- 메모 텍스트 영역 클릭 → inline `<textarea>` 로 전환, Enter/blur 저장 (debounce 500ms PATCH), Esc 취소
- 500자 제한은 클라이언트에서 `maxlength=500` + 서버 중복 검증

### 5.4 보러가기 (`initialTime`)

`current` 스토어 타입 확장:
```ts
// stores/current.ts
export interface CurrentState {
  screen: 'idle' | 'processing' | 'ready' | 'burn_done' | 'error';
  jobId: string | null;
  job: JobDto | null;
  progress: number;
  stageMessage: string;
  errorMessage: string | null;
  initialTime?: number;   // ← 추가 (optional, 초 단위)
}
```

`ReadyScreen.svelte` 에서 소비 — 처음 마운트와 이후 `initialTime` 변경을 **하나의 reactive 블록**으로 통일:

```ts
let lastSeekTarget: number | null = null;

$: if ($current.initialTime !== undefined
        && $current.initialTime !== lastSeekTarget
        && playerRef
        && videoReady) {
  playerRef.seekTo($current.initialTime);
  lastSeekTarget = $current.initialTime;
}
```

- `VideoPlayer.svelte` 는 `onLoadedMetadata` 를 외부로 노출 (없으면 추가). 비디오 메타데이터 로드 완료 후에 `videoReady = true` 를 세팅해야 seek가 실제로 먹힘.
- `lastSeekTarget` 가드로 reactive가 같은 값에 여러 번 재실행되는 걸 방지.
- 이 하나의 블록이 **초기 마운트 + 같은 Job 내 재방문(jobId 동일·initialTime만 변경)** 양쪽을 모두 처리.

### 5.5 새 스토어 `memos`

```ts
// stores/memos.ts
import { writable } from 'svelte/store';
import type { MemoDto } from '$lib/api/types';

export const memos = writable<MemoDto[]>([]);

export async function refreshMemos() {
  const res = await api.listMemos();
  memos.set(res.items);
}
```

Sidebar가 탭 전환 시 / 마운트 시 `refreshMemos()`. 서버가 source of truth.

### 5.6 새 파일 레이아웃

```
backend/app/
├── models/memo.py                ← 신규
├── services/memo.py              ← 신규
└── api/memo.py                   ← 신규

frontend/src/lib/
├── api/memo.ts                   ← 신규
├── stores/memos.ts               ← 신규
├── ui/MemoCard.svelte            ← 신규
└── ui/SegmentMemo.svelte         ← 신규

수정 대상:
- backend/app/api/__init__.py     (신규 라우터 등록)
- backend/app/main.py              (app.include_router)
- backend/app/services/jobs.py     (delete_job 내 memo cascade)
- frontend/src/lib/api/jobs.ts     (ApiError re-export 유지)
- frontend/src/lib/api/types.ts    (MemoDto 추가, CurrentState.initialTime)
- frontend/src/lib/stores/current.ts (initialTime)
- frontend/src/lib/ui/Sidebar.svelte (탭)
- frontend/src/lib/ui/SegmentList.svelte (SegmentMemo 삽입)
- frontend/src/lib/ui/VideoPlayer.svelte (onLoadedMetadata 노출, 필요 시)
- frontend/src/lib/screens/ReadyScreen.svelte (initialTime seek)
```

---

## 6. CLAUDE.md 규약 준수

- 레이어: `api/memo.py` → `services/memo.py` → `models/memo.py` (§2 준수)
- 상태 전이: Memo 생명주기는 `services/memo.py` 에 집중. `job_state.py` 는 Memo를 몰라도 됨.
- 테스트: 신규 서비스·엔드포인트 테스트 동반.
- 컨벤션: Python ruff 규칙, Svelte 컴포넌트 300줄 제한.
- 문서: 이 스펙 + 구현 후 `docs/architecture.md` §4 기능 카탈로그에 메모 항목 추가.

---

## 7. 테스트 전략

### 7.1 Backend (신규 테스트)

| 파일 | 커버 |
|---|---|
| `tests/test_memo_service.py` | 생성·toggle·수정·삭제, UNIQUE 제약, 스냅샷 값, auto-pin side-effect |
| `tests/test_memo_endpoints.py` | POST/GET/PATCH/DELETE 통합, 404 처리 |
| `tests/test_memo_global_list.py` | `/api/memos` 응답 포맷, `job_alive` 판정, 순서(최신순), `limit` 검증 |
| `tests/test_job_delete_cascades_memos.py` | Job 삭제 시 memo들도 삭제됨 |

기존 테스트 전부 그대로 통과해야 함 (회귀 방지).

### 7.2 Frontend

- 프론트엔드 테스트 프레임워크 미도입이라 자동 테스트 없음.
- 수동 smoke: `docs/superpowers/plans/…/phase-N-verify.md` 에 단계 기재.

---

## 8. 예상 파일 변경량

- Backend: 3 신규 파일(models/memo, services/memo, api/memo) + 2 수정(main.py, services/jobs.py) + 4 테스트. 약 600 LoC.
- Frontend: 4 신규 파일(api/memo, stores/memos, MemoCard, SegmentMemo) + 8 수정. 약 500 LoC.
- 문서: 본 스펙 + implementation plan + architecture.md 업데이트.

---

## 9. 리스크와 완화책

| 리스크 | 완화 |
|---|---|
| 메모 있는 영상 자동 pin이 사용자가 모르게 디스크 점유 | Job 삭제 확인 다이얼로그 문구에 메모 개수 명시 ("이 영상의 메모 N개도 함께 삭제됩니다"). 추후 pin 상태 UI에 "자동 북마크됨 — 메모 N개" 라벨 추가는 후속 과제 |
| `segment_text_snapshot`과 실제 segment.text 이탈 (사용자가 segment 편집 시) | `/api/memos` 응답에서 현재 segment.text 우선 사용. 스냅샷은 fallback 전용 |
| 500자 초과 입력 — 프론트/서버 동시 검증 실패 | 서버 Pydantic + DB max_length 양쪽 둔다 |
| `job_alive` 체크가 N+1 쿼리 될 위험 | 단일 `EXISTS` 서브쿼리 또는 JOIN으로 한 번에 |
| 탭 전환 시 깜빡임 | 두 탭 상태 모두 컴포넌트 DOM에 유지, CSS `hidden` 토글 |
| 보러가기 시 비디오 로딩 전 seek 호출로 실패 | `onLoadedMetadata` 콜백에서만 seek (이벤트 보장) |
| 기존 DB 손상 | 기동 시 자동 백업(R6), 배포 전 수동 `docker exec … sqlite3 .dump` 병행 권장 |

---

## 10. 성공 기준

- [ ] `memo` 테이블이 자동 생성되고 기존 `job`/`segment` 데이터 100% 보존.
- [ ] 세그먼트 📎 1클릭으로 저장, 다시 1클릭으로 해제 동작.
- [ ] 사이드바 메모 탭이 전역 리스트 정확히 표시, 카운트 배지 동기화.
- [ ] "보러가기"가 해당 영상으로 이동 + 시작 시점 seek 정확.
- [ ] 메모 있는 영상 자동 pin + Job 삭제 시 경고.
- [ ] 기존 95 테스트 (91 + list_recent 4) 전부 통과. 신규 memo 테스트 전부 pass.
- [ ] docker 재빌드 + 기동 후 기존 job `059ddd86…` 접근 OK (사용자 데이터 무영향).
- [ ] 프론트 빌드 0 errors.

---

## 11. 후속 과제 (이 스펙 밖)

- 메모 50개 이상 쌓일 때 검색/필터.
- 영상별 그룹 뷰 (메모 탭에서 `[전체 / 영상별]` 토글).
- 모바일 최적화 (터치 친화).
- 메모 번역 자동 채움 (언어 학습 모드).
- 메모 내보내기 (CSV, Anki 포맷 등).

---

## 12. 변경 이력

- 2026-04-22: Q1~Q4 브레인스토밍 후 초안 작성.
