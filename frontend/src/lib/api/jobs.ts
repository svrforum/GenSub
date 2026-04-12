import { http } from './client';
import type {
  ConfigDto,
  JobCreateRequest,
  JobDto,
  SegmentDto
} from './types';

export const api = {
  config: () => http.get<ConfigDto>('/api/config'),

  createJob: (req: JobCreateRequest) =>
    http.post<{ job_id: string; status: string }>('/api/jobs', req),

  uploadJob: async (
    file: File,
    model: string,
    language?: string,
    initialPrompt?: string
  ) => {
    const form = new FormData();
    form.append('file', file);
    form.append('model', model);
    if (language) form.append('language', language);
    if (initialPrompt) form.append('initial_prompt', initialPrompt);
    const r = await fetch('/api/jobs/upload', { method: 'POST', body: form });
    if (!r.ok) throw new Error(`upload failed: ${r.status}`);
    return (await r.json()) as { job_id: string; status: string };
  },

  getJob: (id: string) => http.get<JobDto>(`/api/jobs/${id}`),

  cancelJob: (id: string) => http.post<{ ok: boolean }>(`/api/jobs/${id}/cancel`),

  deleteJob: (id: string) => http.del<{ ok: boolean }>(`/api/jobs/${id}`),

  segments: (id: string) => http.get<SegmentDto[]>(`/api/jobs/${id}/segments`),

  patchSegment: (
    id: string,
    idx: number,
    patch: { text?: string; start?: number; end?: number }
  ) => http.patch<{ ok: boolean }>(`/api/jobs/${id}/segments/${idx}`, patch),

  regenerateSegment: (id: string, idx: number) =>
    http.post<{ ok: boolean }>(`/api/jobs/${id}/segments/${idx}/regenerate`),

  searchReplace: (
    id: string,
    find: string,
    replace: string,
    caseSensitive = false
  ) =>
    http.post<{ changed_count: number }>(`/api/jobs/${id}/search_replace`, {
      find,
      replace,
      case_sensitive: caseSensitive
    }),

  triggerBurn: (
    id: string,
    opts: { font?: string; size?: number; outline?: boolean } = {}
  ) =>
    http.post<{ ok: boolean }>(`/api/jobs/${id}/burn`, {
      font: opts.font ?? 'Pretendard',
      size: opts.size ?? 42,
      outline: opts.outline ?? true
    }),

  exportClip: async (
    id: string,
    start: number,
    end: number,
    burnSubtitles = true,
    opts: { font?: string; size?: number; outline?: boolean } = {}
  ) => {
    const resp = await fetch(`/api/jobs/${id}/clip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start,
        end,
        burn_subtitles: burnSubtitles,
        font: opts.font ?? 'Pretendard',
        size: opts.size ?? 42,
        outline: opts.outline ?? true,
      }),
    });
    if (!resp.ok) throw new Error(`clip export failed: ${resp.status}`);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `clip-${start.toFixed(1)}-${end.toFixed(1)}.mp4`;
    a.click();
    URL.revokeObjectURL(url);
  },

  videoUrl: (id: string) => `/api/jobs/${id}/video`,
  vttUrl: (id: string) => `/api/jobs/${id}/subtitles.vtt`,
  srtUrl: (id: string) => `/api/jobs/${id}/subtitles.srt`,
  txtUrl: (id: string) => `/api/jobs/${id}/transcript.txt`,
  jsonUrl: (id: string) => `/api/jobs/${id}/transcript.json`,
  mkvUrl: (id: string) => `/api/jobs/${id}/download/video+subs.mkv`,
  burnedUrl: (id: string) => `/api/jobs/${id}/download/burned.mp4`
};
