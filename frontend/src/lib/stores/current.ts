import { writable } from 'svelte/store';
import type { JobDto } from '$lib/api/types';

export type Screen = 'idle' | 'processing' | 'ready' | 'burn_done' | 'error';

export interface CurrentState {
  screen: Screen;
  jobId: string | null;
  job: JobDto | null;
  progress: number;
  stageMessage: string;
  errorMessage: string | null;
}

const initial: CurrentState = {
  screen: 'idle',
  jobId: null,
  job: null,
  progress: 0,
  stageMessage: '',
  errorMessage: null
};

export const current = writable<CurrentState>(initial);

export function reset() {
  current.set(initial);
}
