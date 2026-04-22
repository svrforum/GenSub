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
  initialTime?: number; // 메모 "보러가기" 시 seek 대상 (초)
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
