# Phase 2 — Frontend: 타입 + API 클라이언트 + 스토어

목표: 검색 UI가 사용할 TypeScript 타입, API 클라이언트, Svelte 스토어를 만든다.

**전제**: Phase 1 완료, pytest 157, `feature/search` 브랜치.

---

### Task 2.1: SearchHit 타입 정의

**Files:**
- Modify: `frontend/src/lib/api/types.ts`

- [ ] **Step 1: 기존 types.ts 확인**

```bash
cd /Users/loki/GenSub
cat frontend/src/lib/api/types.ts | head
```

- [ ] **Step 2: 타입 추가**

`frontend/src/lib/api/types.ts` 파일 말미에 추가:

```ts
// 검색 기능 (2026-04-28 spec)
export type SearchKind = 'job' | 'memo' | 'segment';

export interface SearchHit {
  kind: SearchKind;
  job_id: string;
  job_title: string | null;
  // kind === 'segment' 또는 'memo' 일 때 채워짐
  segment_idx?: number;
  segment_text?: string;
  start?: number;
  end?: number;
  // kind === 'memo' 일 때만
  memo_id?: number;
  memo_text?: string;
}
```

- [ ] **Step 3: 타입체크**

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
git commit -m "feat(search): add SearchHit and SearchKind types

백엔드 GET /api/search 응답 구조와 매칭. kind ('job'|'memo'|'segment')
별로 채워지는 옵셔널 필드 (segment_*, memo_*)."
```

---

### Task 2.2: searchApi 클라이언트

**Files:**
- Create: `frontend/src/lib/api/search.ts`

- [ ] **Step 1: 클라이언트 작성**

Write `frontend/src/lib/api/search.ts`:

```ts
import { http } from './client';
import type { SearchHit } from './types';

export const searchApi = {
  query: (q: string, limit = 50) => {
    const params = new URLSearchParams({ q, limit: String(limit) });
    return http.get<{ items: SearchHit[] }>(`/api/search?${params.toString()}`);
  },
};
```

- [ ] **Step 2: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/api/search.ts
git commit -m "feat(search): add searchApi client

URLSearchParams 로 query 인코딩 (한국어/공백/특수문자 안전).
http 헬퍼 재사용 (jobs.ts, memo.ts 와 동일 패턴)."
```

---

### Task 2.3: 검색 스토어 (sharedState)

**Files:**
- Create: `frontend/src/lib/stores/search.ts`

- [ ] **Step 1: 스토어 작성**

Write `frontend/src/lib/stores/search.ts`:

```ts
import { writable } from 'svelte/store';

import { searchApi } from '$lib/api/search';
import type { SearchHit } from '$lib/api/types';

/** SearchModal open/close. ⌘K 또는 헤더 SearchBar 클릭으로 토글. */
export const searchOpen = writable<boolean>(false);

/** 헤더 SearchBar 와 SearchModal 입력창이 양방향 sync 하는 query. */
export const searchQuery = writable<string>('');

export const searchResults = writable<SearchHit[]>([]);
export const searchLoading = writable<boolean>(false);

let pendingQuery: string | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Debounce 200ms 로 search API 호출. 입력 중간 상태에는 호출 안 함.
 * 같은 query를 연속으로 호출하면 두 번째는 무시.
 */
export function scheduleSearch(query: string): void {
  if (debounceTimer !== null) {
    clearTimeout(debounceTimer);
  }

  const trimmed = query.trim();
  if (trimmed === '') {
    searchResults.set([]);
    searchLoading.set(false);
    return;
  }

  if (trimmed === pendingQuery) return;

  searchLoading.set(true);
  debounceTimer = setTimeout(async () => {
    pendingQuery = trimmed;
    try {
      const res = await searchApi.query(trimmed, 50);
      searchResults.set(res.items);
    } catch {
      searchResults.set([]);
    } finally {
      searchLoading.set(false);
    }
  }, 200);
}

/** 모달 닫기 + 상태 초기화. */
export function closeSearch(): void {
  searchOpen.set(false);
  // 닫을 때 query/results는 보존 (재오픈 시 재사용)
}
```

- [ ] **Step 2: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/stores/search.ts
git commit -m "feat(search): add search store with debounce scheduler

4개 store: searchOpen / searchQuery / searchResults / searchLoading.
scheduleSearch(query): 200ms debounce + 같은 query 중복 호출 방지.
빈 query는 즉시 결과 초기화 (DB hit 없음).
closeSearch(): query/results 보존하며 모달만 닫음 (재오픈 빠름)."
```

---

### Phase 2 완료 검증

- [ ] **Step 1: 프론트 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
npm test 2>&1 | tail -5
```

Expected: 0 errors, 빌드 성공, 4 tests pass (기존).

- [ ] **Step 2: 커밋 로그**

```bash
cd /Users/loki/GenSub
git log --oneline feature/search ^master | cat
```

Expected: 5 커밋 (Phase 1 의 2 + Phase 2 의 3).

Phase 2 완료. Phase 3 진행.
