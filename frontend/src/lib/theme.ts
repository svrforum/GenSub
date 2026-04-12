import { writable } from 'svelte/store';

type Theme = 'light' | 'dark';

const STORAGE_KEY = 'gensub.theme';

function detect(): Theme {
  if (typeof window === 'undefined') return 'light';
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function apply(theme: Theme) {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

export const theme = writable<Theme>('light');

export function initTheme() {
  const initial = detect();
  theme.set(initial);
  apply(initial);
  theme.subscribe((t) => {
    apply(t);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, t);
    }
  });
}

export function toggleTheme() {
  theme.update((t) => (t === 'light' ? 'dark' : 'light'));
}
