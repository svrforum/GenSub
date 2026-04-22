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
