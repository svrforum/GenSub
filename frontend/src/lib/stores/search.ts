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
