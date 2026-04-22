import { writable } from 'svelte/store';

import { memoApi } from '$lib/api/memo';
import type { JobMemoLiteDto } from '$lib/api/types';

/** segment_idx -> memo lite 매핑. O(1) 조회. */
export const jobMemos = writable<Map<number, JobMemoLiteDto>>(new Map());

let currentJobId: string | null = null;

export async function loadJobMemos(jobId: string): Promise<void> {
  if (currentJobId === jobId) return;
  currentJobId = jobId;
  try {
    const res = await memoApi.listForJob(jobId);
    const map = new Map<number, JobMemoLiteDto>();
    for (const m of res.items) {
      map.set(m.segment_idx, m);
    }
    jobMemos.set(map);
  } catch {
    jobMemos.set(new Map());
  }
}

export function clearJobMemos(): void {
  currentJobId = null;
  jobMemos.set(new Map());
}

export function setJobMemo(memo: JobMemoLiteDto): void {
  jobMemos.update((m) => {
    const next = new Map(m);
    next.set(memo.segment_idx, memo);
    return next;
  });
}

export function unsetJobMemo(segmentIdx: number): void {
  jobMemos.update((m) => {
    const next = new Map(m);
    next.delete(segmentIdx);
    return next;
  });
}

export function updateJobMemoText(memoId: number, memoText: string): void {
  jobMemos.update((m) => {
    const next = new Map(m);
    for (const [idx, memo] of next) {
      if (memo.id === memoId) {
        next.set(idx, { ...memo, memo_text: memoText });
        break;
      }
    }
    return next;
  });
}
