# Phase 3 — Frontend: 타입 + API + 스토어 + `current.initialTime`

목표: 메모 UI 구현에 필요한 타입 정의, API 클라이언트, Svelte 스토어, 그리고 "보러가기" 자동 seek을 위한 `current` 스토어 확장.

**전제**: Phase 2 완료, pytest 141 passed, `feature/memo` 브랜치.

---

### Task 3.1: 타입 정의 (`MemoDto`, `MemoListItemDto`)

**Files:**
- Modify: `frontend/src/lib/api/types.ts`

- [ ] **Step 1: 기존 types.ts 확인**

```bash
cat frontend/src/lib/api/types.ts
```

- [ ] **Step 2: 타입 추가**

`frontend/src/lib/api/types.ts` 말미에 추가:

```ts
// 메모 기능 (2026-04-22 spec)
export interface MemoDto {
  id: number;
  job_id: string;
  segment_idx: number;
  memo_text: string;
  segment_text_snapshot: string;
  segment_start: number;
  segment_end: number;
  job_title_snapshot: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoListItemDto {
  id: number;
  job_id: string;
  segment_idx: number;
  memo_text: string;
  segment_text: string;
  start: number;
  end: number;
  job_title: string | null;
  job_alive: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobMemoLiteDto {
  id: number;
  job_id: string;
  segment_idx: number;
  memo_text: string;
}
```

- [ ] **Step 3: 프론트 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npx svelte-kit sync 2>&1 | tail -3
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/api/types.ts
git commit -m "$(cat <<'EOF'
feat(memo): add MemoDto, MemoListItemDto, JobMemoLiteDto types

3가지 DTO:
- MemoDto: POST/PATCH 응답. 스냅샷 필드 포함.
- MemoListItemDto: GET /api/memos 응답 아이템. job_alive + 현재값/스냅샷 merge된 segment_text/job_title.
- JobMemoLiteDto: GET /api/jobs/{id}/memos 경량 응답 (SegmentList 상태 표시용).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.2: API 클라이언트 (`api/memo.ts`)

**Files:**
- Create: `frontend/src/lib/api/memo.ts`

- [ ] **Step 1: 기존 api/jobs.ts 클라이언트 패턴 참고**

```bash
head -30 frontend/src/lib/api/jobs.ts
```

`http` 헬퍼와 `ApiError` 사용 방식 확인.

- [ ] **Step 2: memo 클라이언트 작성**

Write `frontend/src/lib/api/memo.ts`:

```ts
import { http } from './client';
import type { JobMemoLiteDto, MemoDto, MemoListItemDto } from './types';

export interface ToggleMemoResult {
  ok: boolean;
  action: 'created' | 'deleted';
  memo?: MemoDto;
}

export const memoApi = {
  toggleSave: (jobId: string, idx: number) =>
    http.post<ToggleMemoResult>(`/api/jobs/${jobId}/segments/${idx}/memo`),

  updateText: (memoId: number, memoText: string) =>
    http.patch<{ ok: boolean; memo: MemoDto }>(`/api/memos/${memoId}`, {
      memo_text: memoText,
    }),

  delete: (memoId: number) =>
    http.del<{ ok: boolean }>(`/api/memos/${memoId}`),

  listGlobal: (limit = 100) =>
    http.get<{ items: MemoListItemDto[] }>(`/api/memos?limit=${limit}`),

  listForJob: (jobId: string) =>
    http.get<{ items: JobMemoLiteDto[] }>(`/api/jobs/${jobId}/memos`),
};
```

- [ ] **Step 3: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/api/memo.ts
git commit -m "$(cat <<'EOF'
feat(memo): add memoApi client for 5 endpoints

memoApi.toggleSave/updateText/delete/listGlobal/listForJob.
ApiError는 기존 client.ts의 것을 재사용 (jobs.ts와 동일 패턴).

ToggleMemoResult 타입으로 POST 응답 "action" 분기 처리.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.3: 스토어 — `memos` (전역 리스트)

**Files:**
- Create: `frontend/src/lib/stores/memos.ts`

- [ ] **Step 1: 기존 `stores/history.ts` 패턴 참고**

```bash
head -30 frontend/src/lib/stores/history.ts
```

- [ ] **Step 2: 스토어 작성**

Write `frontend/src/lib/stores/memos.ts`:

```ts
import { writable } from 'svelte/store';

import { memoApi } from '$lib/api/memo';
import type { MemoListItemDto } from '$lib/api/types';

export const memos = writable<MemoListItemDto[]>([]);

let loading = false;

export async function refreshMemos(): Promise<void> {
  if (loading) return;
  loading = true;
  try {
    const res = await memoApi.listGlobal(100);
    memos.set(res.items);
  } catch {
    // 네트워크 오류 등 — 조용히 기존 목록 유지 (refresh bug 방지)
  } finally {
    loading = false;
  }
}

/**
 * 로컬 낙관적 업데이트: 새로 생성된 메모를 목록 최상단에 추가.
 * 서버 round-trip 없이 즉시 UI 반영용. 이어서 refreshMemos() 로 최종 동기화 권장.
 */
export function addMemoOptimistic(item: MemoListItemDto): void {
  memos.update((list) => [item, ...list.filter((m) => m.id !== item.id)]);
}

/**
 * 로컬 삭제 — 삭제 낙관적 업데이트 또는 server 이벤트 반영.
 */
export function removeMemoLocal(memoId: number): void {
  memos.update((list) => list.filter((m) => m.id !== memoId));
}

/**
 * 단일 아이템 업데이트 (PATCH 결과 반영).
 */
export function updateMemoLocal(memoId: number, patch: Partial<MemoListItemDto>): void {
  memos.update((list) =>
    list.map((m) => (m.id === memoId ? { ...m, ...patch } : m)),
  );
}
```

- [ ] **Step 3: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/stores/memos.ts
git commit -m "$(cat <<'EOF'
feat(memo): add memos store with optimistic update helpers

writable<MemoListItemDto[]> + refreshMemos() + 3개 local helpers
(add/remove/update). 네트워크 오류는 조용히 삼켜서 기존 목록 유지.

Phase 4·5에서 SegmentMemo와 MemoCard가 이 스토어 사용.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3.4: `current` 스토어에 `initialTime` 추가

**Files:**
- Modify: `frontend/src/lib/stores/current.ts`

- [ ] **Step 1: 현재 스토어 확인**

```bash
cat frontend/src/lib/stores/current.ts
```

- [ ] **Step 2: 타입 확장**

Edit `frontend/src/lib/stores/current.ts`. 인터페이스에 `initialTime?: number` 추가. 예:

```ts
// 변경 전 (패턴 예시):
export interface CurrentState {
  screen: 'idle' | 'processing' | 'ready' | 'burn_done' | 'error';
  jobId: string | null;
  job: JobDto | null;
  progress: number;
  stageMessage: string;
  errorMessage: string | null;
}

// 변경 후:
export interface CurrentState {
  screen: 'idle' | 'processing' | 'ready' | 'burn_done' | 'error';
  jobId: string | null;
  job: JobDto | null;
  progress: number;
  stageMessage: string;
  errorMessage: string | null;
  initialTime?: number; // 메모 "보러가기" 시 seek 대상 (초)
}
```

`reset()` / 초기 state에 새 필드 기본값 필요 없음 (optional).

- [ ] **Step 3: `openMemo` 헬퍼 추가**

같은 파일 말미에 추가:

```ts
/**
 * 메모 "보러가기" 동작: 해당 Job의 ReadyScreen으로 전환 + 시작 시점 seek.
 * ReadyScreen.svelte가 `initialTime` 변화를 reactive로 감지하여 VideoPlayer.seekTo 호출.
 */
export function openMemo(jobId: string, start: number): void {
  current.set({
    screen: 'ready',
    jobId,
    job: null,
    progress: 1,
    stageMessage: '',
    errorMessage: null,
    initialTime: start,
  });
}
```

(`current.set` 및 `reset` 같은 기존 export 근처.)

- [ ] **Step 4: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors. 만약 `initialTime` 을 필수로 취급하는 기존 호출이 있다면 기본값 분기 필요.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/stores/current.ts
git commit -m "$(cat <<'EOF'
feat(memo): add CurrentState.initialTime and openMemo helper

스펙 §5.4: 메모 "보러가기" 시 ReadyScreen으로 이동 + 해당 시점 seek.
initialTime은 optional number (초). ReadyScreen이 Phase 5에서
reactive로 소비하여 VideoPlayer.seekTo 호출.

openMemo(jobId, start): 메모 카드 클릭 핸들러용 헬퍼.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Phase 3 완료 검증

- [ ] **Step 1: 프론트 타입 체크 + 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

Expected: 0 errors, 빌드 성공.

- [ ] **Step 2: 백엔드 테스트 회귀 (변경 없으니 그대로여야)**

```bash
cd ../backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 141 passed.

- [ ] **Step 3: 커밋 로그**

```bash
cd /Users/loki/GenSub
git log --oneline feature/memo ^master | cat
```

Expected: 11개 커밋 (Phase 1·2 7개 + Phase 3 4개).

Phase 3 완료.
