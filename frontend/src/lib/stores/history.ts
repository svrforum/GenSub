import { writable } from 'svelte/store';

const STORAGE_KEY = 'gensub.history';
const MAX = 10;

export interface HistoryItem {
  jobId: string;
  title: string | null;
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
    const next = [item, ...items.filter((x) => x.jobId !== item.jobId)];
    save(next);
    return next.slice(0, MAX);
  });
}

export function removeFromHistory(jobId: string) {
  history.update((items) => {
    const next = items.filter((x) => x.jobId !== jobId);
    save(next);
    return next;
  });
}
