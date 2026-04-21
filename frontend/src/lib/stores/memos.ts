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
