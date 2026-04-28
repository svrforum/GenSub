# Phase 9 — Frontend API Client + Stores

백엔드와 통신하는 얇은 API 계층과, 현재 작업 상태를 관리하는 Svelte 스토어를 만든다. 이후 화면 컴포넌트는 이 레이어만 사용하므로 타입 안정성과 단일 책임에 집중한다.

**사전 조건**: Phase 8 완료 (프리미티브 컴포넌트 준비).

---

### Task 9.1: 타입 정의

**Files:**
- Create: `frontend/src/lib/api/types.ts`

- [ ] **Step 1: 공유 타입 작성**

Write `frontend/src/lib/api/types.ts`:

```typescript
export type JobStatus =
 | 'pending'
 | 'downloading'
 | 'transcribing'
 | 'ready'
 | 'burning'
 | 'done'
 | 'failed';

export type ModelName = 'tiny' | 'base' | 'small' | 'medium' | 'large-v3';

export interface JobDto {
 id: string;
 source_url: string | null;
 source_kind: 'url' | 'upload';
 title: string | null;
 duration_sec: number | null;
 language: string | null;
 model_name: string;
 status: JobStatus;
 progress: number;
 stage_message: string | null;
 error_message: string | null;
 created_at: string;
 updated_at: string;
 expires_at: string;
 cancel_requested: boolean;
}

export interface SegmentDto {
 idx: number;
 start: number;
 end: number;
 text: string;
 avg_logprob: number | null;
 no_speech_prob: number | null;
 edited: boolean;
}

export interface ConfigDto {
 default_model: ModelName;
 available_models: ModelName[];
 max_video_minutes: number;
 max_upload_mb: number;
 job_ttl_hours: number;
 has_openai_fallback: boolean;
}

export interface JobCreateRequest {
 url?: string;
 model: ModelName;
 language?: string;
 initial_prompt?: string;
}

export interface ProgressEvent {
 status: JobStatus;
 progress: number;
 stage_message: string | null;
}
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/api/types.ts
git commit -m "feat(frontend): add API type definitions"
```

---

### Task 9.2: fetch 래퍼

**Files:**
- Create: `frontend/src/lib/api/client.ts`

- [ ] **Step 1: 클라이언트 작성**

Write `frontend/src/lib/api/client.ts`:

```typescript
const BASE = ''; // 동일 오리진 서빙 전제 (개발 시 Vite proxy로 처리)

export class ApiError extends Error {
 constructor(public status: number, public detail: string) {
 super(`HTTP ${status}: ${detail}`);
 }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
 const resp = await fetch(`${BASE}${path}`, {
 ...init,
 headers: {
 'Content-Type': 'application/json',
 ...(init.headers || {})
 }
 });
 if (!resp.ok) {
 let detail = resp.statusText;
 try {
 const body = await resp.json();
 detail = body.detail || JSON.stringify(body);
 } catch {
 /* non-JSON response */
 }
 throw new ApiError(resp.status, detail);
 }
 if (resp.status === 204) return undefined as T;
 return (await resp.json()) as T;
}

export const http = {
 get: <T>(path: string) => request<T>(path, { method: 'GET' }),
 post: <T>(path: string, body?: unknown) =>
 request<T>(path, {
 method: 'POST',
 body: body === undefined ? undefined : JSON.stringify(body)
 }),
 patch: <T>(path: string, body: unknown) =>
 request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
 del: <T>(path: string) => request<T>(path, { method: 'DELETE' })
};
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/api/client.ts
git commit -m "feat(frontend): add typed fetch wrapper with ApiError"
```

---

### Task 9.3: Jobs API

**Files:**
- Create: `frontend/src/lib/api/jobs.ts`

- [ ] **Step 1: 작성**

Write `frontend/src/lib/api/jobs.ts`:

```typescript
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

 videoUrl: (id: string) => `/api/jobs/${id}/video`,
 vttUrl: (id: string) => `/api/jobs/${id}/subtitles.vtt`,
 srtUrl: (id: string) => `/api/jobs/${id}/subtitles.srt`,
 txtUrl: (id: string) => `/api/jobs/${id}/transcript.txt`,
 jsonUrl: (id: string) => `/api/jobs/${id}/transcript.json`,
 mkvUrl: (id: string) => `/api/jobs/${id}/download/video+subs.mkv`,
 burnedUrl: (id: string) => `/api/jobs/${id}/download/burned.mp4`
};
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/api/jobs.ts
git commit -m "feat(frontend): add Jobs API client functions"
```

---

### Task 9.4: SSE 이벤트 구독 헬퍼

**Files:**
- Create: `frontend/src/lib/api/events.ts`

- [ ] **Step 1: 작성**

Write `frontend/src/lib/api/events.ts`:

```typescript
import type { ProgressEvent } from './types';

export interface EventHandlers {
 onProgress?: (event: ProgressEvent) => void;
 onDone?: (status: string) => void;
 onError?: (message: string) => void;
}

export function subscribeJobEvents(jobId: string, handlers: EventHandlers): () => void {
 const es = new EventSource(`/api/jobs/${jobId}/events`);

 es.addEventListener('progress', (evt) => {
 try {
 const data = JSON.parse((evt as MessageEvent).data) as ProgressEvent;
 handlers.onProgress?.(data);
 } catch {
 /* ignore malformed */
 }
 });

 es.addEventListener('done', (evt) => {
 try {
 const data = JSON.parse((evt as MessageEvent).data) as { status: string };
 handlers.onDone?.(data.status);
 } catch {
 handlers.onDone?.('ready');
 }
 es.close();
 });

 es.addEventListener('error', (evt) => {
 if ((evt as MessageEvent).data) {
 try {
 const data = JSON.parse((evt as MessageEvent).data) as { message: string };
 handlers.onError?.(data.message);
 } catch {
 handlers.onError?.('unknown error');
 }
 es.close();
 }
 });

 return () => es.close();
}
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/api/events.ts
git commit -m "feat(frontend): add SSE event subscription helper"
```

---

### Task 9.5: 현재 작업 스토어 + localStorage 히스토리

**Files:**
- Create: `frontend/src/lib/stores/current.ts`
- Create: `frontend/src/lib/stores/history.ts`

- [ ] **Step 1: current 스토어**

Write `frontend/src/lib/stores/current.ts`:

```typescript
import { writable } from 'svelte/store';
import type { JobDto } from '$lib/api/types';

export type Screen = 'idle' | 'processing' | 'ready' | 'error';

export interface CurrentState {
 screen: Screen;
 job: JobDto | null;
 progress: number;
 stageMessage: string;
 errorMessage: string | null;
}

const initial: CurrentState = {
 screen: 'idle',
 job: null,
 progress: 0,
 stageMessage: '',
 errorMessage: null
};

export const current = writable<CurrentState>(initial);

export function reset() {
 current.set(initial);
}
```

- [ ] **Step 2: history 스토어**

Write `frontend/src/lib/stores/history.ts`:

```typescript
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
```

- [ ] **Step 3: layout에서 history 초기화**

Modify `frontend/src/routes/+layout.svelte`: `onMount` 안에 `initHistory()` 호출 추가.

Overwrite `frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
 import '../app.css';
 import { onMount } from 'svelte';
 import { initTheme } from '$lib/theme';
 import { initHistory } from '$lib/stores/history';

 onMount(() => {
 initTheme();
 initHistory();
 });
</script>

<slot />
```

- [ ] **Step 4: 빌드 검증**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/stores/ frontend/src/routes/+layout.svelte
git commit -m "feat(frontend): add current and history stores"
```

---
