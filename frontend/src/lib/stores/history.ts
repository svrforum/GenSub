import { writable } from 'svelte/store';

const STORAGE_KEY = 'gensub.history';
const MAX = 10;

export interface HistoryItem {
  jobId: string;
  title: string | null;
  originalTitle?: string | null;
  bookmarked?: boolean;
  createdAt: string;
}

function load(): HistoryItem[] {
  if (typeof localStorage === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as HistoryItem[]) : [];
  } catch {
    return [];
  }
}

function save(items: HistoryItem[]) {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX)));
}

export const history = writable<HistoryItem[]>([]);

export function initHistory() {
  history.set(load());
}

export function pushHistory(item: HistoryItem) {
  history.update((items) => {
    const existing = items.find((x) => x.jobId === item.jobId);
    // 원제목 보존: 기존 항목에 originalTitle이 있으면 유지
    const originalTitle =
      item.originalTitle ?? existing?.originalTitle ?? existing?.title ?? item.title;
    const merged = { ...item, originalTitle };
    const next = [merged, ...items.filter((x) => x.jobId !== item.jobId)];
    save(next);
    return next.slice(0, MAX);
  });
}

export function renameHistory(jobId: string, newTitle: string) {
  history.update((items) => {
    const next = items.map((x) =>
      x.jobId === jobId ? { ...x, title: newTitle } : x
    );
    save(next);
    return next;
  });
}

export function toggleBookmark(jobId: string) {
  history.update((items) => {
    const next = items.map((x) =>
      x.jobId === jobId ? { ...x, bookmarked: !x.bookmarked } : x
    );
    save(next);
    return next;
  });
}

export function removeFromHistory(jobId: string) {
  history.update((items) => {
    const next = items.filter((x) => x.jobId !== jobId);
    save(next);
    return next;
  });
}
