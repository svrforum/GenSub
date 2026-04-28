# 검색 기능 설계 명세 (자막·메모·영상 통합)

**날짜**: 2026-04-28
**프로젝트**: GenSub
**목적**: 사용자가 쌓아둔 자막·메모·영상을 **빠르게 찾고 해당 시점으로 점프**할 수 있게 한다.
**스펙 성격**: 신규 기능. 기존 스키마·UI 무변경, 덧붙이는 방식.

---

## 1. 배경

GenSub은 자체호스팅 자막 아카이브 도구. 사용 시간이 늘수록 영상·메모·자막 데이터가 누적된다. 현재는 사이드바 리스트 스크롤로만 찾을 수 있어, 누적량이 많아지면 "어디서 들었더라" 같은 회상 검색이 비현실적이다.

**페르소나(한국 자체호스팅 사용자) 핵심 니즈:**
- 자기 데이터에서 풀텍스트로 빨리 찾기
- 키보드 중심 (CLI/홈서버 익숙)
- 검색 결과 → 해당 영상 + 해당 시점으로 즉시 점프

## 2. Goals / Non-Goals

### Goals
1. **전역 검색**: 모든 영상의 자막 + 모든 메모 + 영상 제목을 한 검색으로.
2. **영상 내 검색**: ReadyScreen 안에서 ⌘F로 현재 자막을 빠르게 필터·점프.
3. **즉시 점프**: 검색 결과 클릭 → 해당 영상 + 해당 시점 (메모 "보러가기"와 동일 흐름).
4. **데이터 안전**: 기존 스키마·인덱스 무변경, LIKE 풀스캔으로 시작.

### Non-Goals
- FTS5 등 정식 풀텍스트 인덱스. 페르소나 규모(영상 100~1000개)에선 LIKE 충분.
- 검색 히스토리·자동완성·제안.
- 정규식 검색.
- kind/날짜/언어 필터.
- 모바일 터치 UX.

## 3. 사용자 흐름

### 전역 검색 (⌘K + 헤더 검색바)
1. 사용자가 ⌘K (또는 헤더 검색바 클릭) → 화면 중앙에 모달 열림
2. 검색어 입력 → 200ms debounce 후 `GET /api/search?q=...`
3. 결과 카드들이 모달에 표시 (영상 → 메모 → 자막 순)
4. 결과 클릭 → 모달 닫힘 + 해당 영상으로 이동 + 해당 시점 seek
5. Esc 또는 외부 클릭 → 모달 닫힘

### 영상 내 검색 (⌘F)
1. ReadyScreen 안에서 ⌘F → 브라우저 기본 검색 차단, 자체 오버레이 열림
2. 검색어 입력 → 즉시 매치 (이미 로드된 segments 배열 클라이언트 필터)
3. 매치된 세그먼트 시각적 강조 + "3/12" 카운트 표시
4. Enter / ↓ → 다음 매치로 점프 (영상 seek + 세그먼트 스크롤)
5. Shift+Enter / ↑ → 이전 매치
6. Esc → 닫고 강조 해제

## 4. 백엔드 설계

### 4.1 데이터 모델

**무변경.** 기존 `Job`(`title`), `Segment`(`text`), `Memo`(`memo_text`, `segment_text_snapshot`) 컬럼 활용.

새 테이블·인덱스 없음. SQLite의 `LIKE '%query%'`는 인덱스 없이 풀스캔이지만, 페르소나 규모에선 즉시 응답.

### 4.2 서비스 레이어

**파일**: `backend/app/services/search.py` (신규)

```python
@dataclass
class SearchHit:
    kind: Literal["job", "memo", "segment"]
    job_id: str
    job_title: str | None
    # kind == "segment"
    segment_idx: int | None = None
    segment_text: str | None = None
    start: float | None = None
    end: float | None = None
    # kind == "memo"
    memo_id: int | None = None
    memo_text: str | None = None


def search_all(engine: Engine, query: str, limit: int = 50) -> list[SearchHit]:
    """대소문자 구분 없는 부분 매치 검색.

    - Job.title LIKE
    - Memo.memo_text OR Memo.segment_text_snapshot LIKE
    - Segment.text LIKE (현재 살아있는 Job의 segment만)
    결과 순서: job → memo → segment, 각 그룹 내 updated_at desc.
    빈 query는 빈 리스트 반환.
    """
```

**구현 핵심**:
- 빈/공백 query 입력 → `[]` 즉시 반환 (DB 호출 안 함).
- LIKE 패턴: `f"%{query}%"`. SQLite의 LIKE는 ASCII에서만 case-insensitive. 한국어는 자체로 대소문자 구분 없음.
- 3개 별도 select 후 파이썬에서 합치고 정렬. UNION ALL 같은 SQL 트릭 안 씀 (가독성 우선).
- limit은 전체 합산 limit. 그룹별 분배는 안 함 (50건이면 영상 다 보여도 충분).
- Memo 결과: `Job.id`로 join해서 `job_title` 채움. Job이 없는 orphan memo는 `job_title=None`. (현 구현상 Job 삭제 시 cascade라 발생 빈도 낮지만 처리는 함.)

### 4.3 API

**파일**: `backend/app/api/search.py` (신규)

```python
@router.get("/api/search")
def search(request: Request, q: str = "", limit: int = 50) -> dict:
    hits = search_all(request.app.state.engine, q, limit=limit)
    return {"items": [_hit_to_dict(h) for h in hits]}
```

`_hit_to_dict`: dataclass → JSON-friendly dict. `kind` 별로 채워진 필드만 반환 (None은 제외).

`main.py`에 `app.include_router(search_router)` 추가.

### 4.4 테스트

`backend/tests/test_search.py` (신규):

| 케이스 | 검증 |
|---|---|
| `test_search_empty_query_returns_empty` | `q=""` → `[]` |
| `test_search_matches_segment_text` | 자막에 "hello" 있을 때 검색 결과 |
| `test_search_matches_memo_text` | 메모에 "중요" 있을 때 |
| `test_search_matches_job_title` | 영상 제목 매치 |
| `test_search_korean_substring` | "안녕" 포함 자막 발견 |
| `test_search_case_insensitive_ascii` | "Hello" 검색이 "hello" 매치 |
| `test_search_respects_limit` | limit=2면 최대 2건 |
| `test_search_excludes_orphan_segments` | Job 없는 segment는 매치 안 됨 (현재 cascade로 발생 안 하지만 방어) |
| `test_search_endpoint_integration` | TestClient로 GET /api/search 응답 포맷 |

기준선 142 → +9 = 151 backend tests.

## 5. 프론트엔드 설계

### 5.1 API 클라이언트

**파일**: `frontend/src/lib/api/search.ts` (신규)

```ts
export type SearchKind = 'job' | 'memo' | 'segment';

export interface SearchHit {
  kind: SearchKind;
  job_id: string;
  job_title: string | null;
  segment_idx?: number;
  segment_text?: string;
  start?: number;
  end?: number;
  memo_id?: number;
  memo_text?: string;
}

export const searchApi = {
  query: (q: string, limit = 50) =>
    http.get<{ items: SearchHit[] }>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};
```

### 5.2 헤더 SearchBar (visible)

**파일**: `frontend/src/lib/ui/SearchBar.svelte` (신규)

- 위치: `+layout.svelte` 헤더 가운데 (다크모드 토글 왼쪽)
- 너비 ~360px, 좌측에 search 아이콘
- placeholder: "자막·메모·영상 검색…"
- 클릭/포커스 → `searchOpen` 스토어 set true → `SearchModal` 열림
- 헤더 입력값과 모달 입력값은 같은 스토어로 sync

### 5.3 ⌘K 글로벌 단축키

**파일**: `+layout.svelte` 수정

```ts
function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    searchOpen.set(true);
  }
}
```

`window.addEventListener('keydown', handleKeydown)` in `onMount`, cleanup in `onDestroy`.

### 5.4 SearchModal

**파일**: `frontend/src/lib/ui/SearchModal.svelte` (신규)

UI:
- 화면 중앙 fixed, 너비 640px, max-h 500px, 상단 64px offset
- 백드롭 dim + click 외부 닫힘
- 입력창 (자동 포커스) + 결과 리스트 스크롤
- 결과 카드 3종 (`kind`로 분기):
  - `job`: 🎬 + 영상 제목
  - `memo`: 📎 + 메모 텍스트(없으면 segment_text) + 영상 제목 + MM:SS
  - `segment`: 💬 + 자막 텍스트 + 영상 제목 + MM:SS
- Esc 닫기, 외부 클릭 닫기
- 입력 변경 시 200ms debounce → `searchApi.query()`
- 결과 클릭 → `openMemo(job_id, start ?? 0)` (이미 있는 헬퍼) → 모달 닫힘

상태 관리:
- 새 스토어 `frontend/src/lib/stores/search.ts`:
  - `searchOpen: Writable<boolean>`
  - `searchQuery: Writable<string>` — 헤더 SearchBar와 모달이 양방향 sync
  - `searchResults: Writable<SearchHit[]>`
  - `searchLoading: Writable<boolean>`

### 5.5 영상 내 검색 (InVideoSearchOverlay)

**파일**: `frontend/src/lib/ui/InVideoSearchOverlay.svelte` (신규)

- ReadyScreen 안에서만 활성화
- ⌘F 캡처 시 오버레이 노출 (브라우저 기본 검색 막음)
- 작은 입력창 + "3/12" 카운트 + ↑↓ 네비게이션 버튼
- segment 배열 클라이언트 필터 (`segment.text.toLowerCase().includes(q.toLowerCase())`)
- 매치 인덱스 배열 유지, current pointer로 현재 매치 지정
- Enter / ↓ → next, Shift+Enter / ↑ → prev
- 매치된 segment에 노란색 배경 (예: `bg-yellow-500/20`)
- 현재 매치는 더 진한 강조 (예: `bg-yellow-500/40` + 좌측 노란 바)
- 매치 점프 시 `playerRef.seekTo(segment.start)` + segment list scroll-into-view
- Esc → 닫고 매치 강조 모두 제거

`SegmentList.svelte`에 prop으로 `highlightedIdxs: Set<number>`, `currentMatchIdx: number | null` 받아 시각적 강조 적용.

### 5.6 키 매핑

| 단축키 | 컨텍스트 | 동작 |
|---|---|---|
| ⌘K / Ctrl+K | 어디서든 | 전역 검색 모달 열기 |
| 헤더 SearchBar 클릭 | 헤더 | 전역 검색 모달 열기 (포커스됨) |
| ⌘F / Ctrl+F | ReadyScreen 내부 | 영상 내 검색 오버레이 |
| Enter | 영상 내 검색 | 다음 매치로 |
| Shift+Enter | 영상 내 검색 | 이전 매치로 |
| Esc | 둘 다 | 닫기 |

⌘F는 ReadyScreen이 마운트된 동안만 가로채고, 다른 화면에선 브라우저 기본 동작 유지.

## 6. CLAUDE.md / CONVENTIONS.md 규약 준수

- `api/search.py` 라우터는 `services/search.py`만 호출 (Session 직접 사용 금지)
- 새 컴포넌트들 모두 `<script lang="ts">`, 1000줄 한참 이내
- 스토어는 `stores/search.ts`에만, 컴포넌트에서 `localStorage` 직접 접근 안 함

## 7. 마이그레이션 안전성

- 새 테이블·인덱스·컬럼 없음 → schema 변경 0
- 신규 코드 추가만, 기존 코드 수정 최소 (`+layout.svelte`, `ReadyScreen.svelte`, `main.py`만)
- 롤백 시 영향 없음
- 기존 142 backend tests + 4 frontend tests 그대로 통과해야 함

## 8. 리스크 및 완화

| 리스크 | 완화 |
|---|---|
| LIKE 풀스캔이 100k+ 세그먼트에서 느려짐 | 페르소나 규모(<1000영상)에선 미발생. 발생 시 FTS5 마이그레이션 별도 스펙. |
| ⌘F 오버레이가 SegmentList 스크롤과 충돌 | 매치 점프 시 `scrollIntoView({ block: 'center' })` 사용 |
| 모달과 in-video 오버레이 동시 활성화 | SearchModal이 활성이면 ReadyScreen의 ⌘F 핸들러는 무시. 또는 ⌘K가 우선 |
| 200ms debounce 안에서 typing 지속 시 stale 결과 | abort controller로 이전 fetch cancel — 단순화 위해 v1에선 latest-wins (debounce만으로 충분) |
| 한국어 unicode normalization 차이 | 기본 Python str + LIKE면 NFC 정규화는 입력 양쪽 동일하다고 가정. 발생 시 NFC 변환 추가 |

## 9. 성공 기준

- [ ] `GET /api/search?q=test` 정상 동작, 빈/한국어/영문/매치 없음 케이스 모두 OK
- [ ] 헤더 SearchBar 클릭 → 모달 열림, 입력 → 결과 표시, 결과 클릭 → 영상으로 이동 + seek
- [ ] ⌘K → 모달 열림 (어디서나)
- [ ] ReadyScreen ⌘F → 오버레이 열림, 입력 → 매치 강조, Enter → 다음 점프
- [ ] Esc → 닫기 동작
- [ ] 백엔드 142 → 151+ tests, 모두 pass
- [ ] 프론트 0 svelte-check errors, 4 frontend tests 그대로 pass
- [ ] docker compose 재빌드 후 동작 확인

## 10. 후속 (Non-goals 재확인)

- FTS5 인덱스 마이그레이션 (성능 이슈 시)
- 검색 히스토리 / 즐겨찾기 검색어
- 정규식 / 와일드카드
- kind / 날짜 / 언어 필터 UI
- 모바일 터치 UX

## 11. 변경 이력

- 2026-04-28: 초안 작성. Q1=C(자막+메모+제목), Q2=D+B(⌘K 모달 + 헤더 검색바 둘 다), Q3=A(LIKE).
