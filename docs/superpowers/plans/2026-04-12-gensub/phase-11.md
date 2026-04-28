# Phase 11 — Processing Screen (Step 2)

### Task 11.1: ProcessingScreen 컴포넌트

**Files:**
- Create: `frontend/src/lib/screens/ProcessingScreen.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: 작성**

Write `frontend/src/lib/screens/ProcessingScreen.svelte`:

```svelte
<script lang="ts">
 import { onMount, onDestroy } from 'svelte';
 import CircularProgress from '$lib/ui/CircularProgress.svelte';
 import Button from '$lib/ui/Button.svelte';
 import { api } from '$lib/api/jobs';
 import { subscribeJobEvents } from '$lib/api/events';
 import { current, reset } from '$lib/stores/current';

 export let jobId: string;

 let unsubscribe: (() => void) | null = null;
 let title = '';

 const stageCopy: Record<string, string> = {
 pending: '준비하고 있어요',
 downloading: '영상을 가져오고 있어요',
 transcribing: '음성을 듣고 있어요',
 burning: '자막을 영상에 입히고 있어요'
 };

 onMount(async () => {
 try {
 const job = await api.getJob(jobId);
 title = job.title ?? job.source_url ?? '';
 current.update((c) => ({ ...c, job, stageMessage: stageCopy[job.status] ?? c.stageMessage }));
 } catch {}

 unsubscribe = subscribeJobEvents(jobId, {
 onProgress(evt) {
 current.update((c) => ({
 ...c,
 progress: evt.progress,
 stageMessage:
 evt.stage_message ?? stageCopy[evt.status] ?? c.stageMessage
 }));
 },
 onDone(status) {
 if (status === 'ready' || status === 'done') {
 current.update((c) => ({ ...c, screen: 'ready', progress: 1 }));
 }
 },
 onError(message) {
 current.update((c) => ({
 ...c,
 screen: 'error',
 errorMessage: message
 }));
 }
 });
 });

 onDestroy(() => {
 unsubscribe?.();
 });

 async function cancel() {
 try {
 await api.cancelJob(jobId);
 } catch {}
 reset();
 }
</script>

<div class="min-h-screen flex items-center justify-center px-6">
 <div class="flex flex-col items-center gap-12 max-w-md w-full">
 {#if title}
 <div class="card px-6 py-4 w-full text-center">
 <div class="text-body font-semibold truncate">{title}</div>
 </div>
 {/if}

 <CircularProgress value={$current.progress} />

 <div class="text-center">
 <div class="text-title">{$current.stageMessage}</div>
 </div>

 <Button variant="ghost" on:click={cancel}>취소</Button>
 </div>
</div>
```

- [ ] **Step 2: +page.svelte에 ProcessingScreen 분기 추가**

Overwrite `frontend/src/routes/+page.svelte`:

```svelte
<script lang="ts">
 import { current } from '$lib/stores/current';
 import IdleScreen from '$lib/screens/IdleScreen.svelte';
 import ProcessingScreen from '$lib/screens/ProcessingScreen.svelte';

 $: jobId = typeof window !== 'undefined' ? (window as any).__gensubCurrentJobId as string | undefined : undefined;
</script>

{#if $current.screen === 'idle'}
 <IdleScreen />
{:else if $current.screen === 'processing' && jobId}
 <ProcessingScreen {jobId} />
{:else if $current.screen === 'ready' && jobId}
 <div class="min-h-screen flex items-center justify-center">
 <p class="text-body">Ready (Phase 12에서 구현)</p>
 </div>
{:else if $current.screen === 'error'}
 <div class="min-h-screen flex items-center justify-center">
 <div class="text-center">
 <div class="text-title text-danger mb-2">문제가 생겼어요</div>
 <div class="text-body text-text-secondary-light dark:text-text-secondary-dark">
 {$current.errorMessage ?? '알 수 없는 오류'}
 </div>
 </div>
 </div>
{/if}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/ProcessingScreen.svelte frontend/src/routes/+page.svelte
git commit -m "feat(frontend): add ProcessingScreen with circular progress and SSE"
```

---

### Task 11.2: 카피 로테이션 (정지감 방지)

**Files:**
- Modify: `frontend/src/lib/screens/ProcessingScreen.svelte`

- [ ] **Step 1: 카피 배열 + 10초마다 변경**

Modify `frontend/src/lib/screens/ProcessingScreen.svelte` script: 카피 로테이션 로직 추가.

```typescript
const rotatingCopy: Record<string, string[]> = {
 pending: ['준비하고 있어요', '잠시만요'],
 downloading: ['영상을 가져오고 있어요', '네트워크에서 받는 중이에요', '거의 다 왔어요'],
 transcribing: [
 '음성을 듣고 있어요',
 '단어를 받아쓰고 있어요',
 '타임스탬프를 맞추고 있어요'
 ],
 burning: [
 '자막을 영상에 입히고 있어요',
 '프레임마다 자막을 그리고 있어요',
 '거의 끝났어요'
 ]
};

let rotationTimer: ReturnType<typeof setInterval> | null = null;
let rotationIdx = 0;

function applyRotatingCopy(status: string) {
 const arr = rotatingCopy[status];
 if (!arr) return;
 current.update((c) => ({ ...c, stageMessage: arr[rotationIdx % arr.length] }));
}

onMount(() => {
 rotationTimer = setInterval(() => {
 rotationIdx += 1;
 const st = $current.job?.status ?? 'pending';
 applyRotatingCopy(st);
 }, 10000);
});

onDestroy(() => {
 if (rotationTimer) clearInterval(rotationTimer);
});
```

이 블록을 기존 `onMount` 안 또는 별도의 `onMount`에 통합한다. (여러 `onMount`는 Svelte에서 한 파일에 하나만 허용되므로 기존 onMount에 머지.)

최종 onMount 형태:

```typescript
onMount(async () => {
 try {
 const job = await api.getJob(jobId);
 title = job.title ?? job.source_url ?? '';
 current.update((c) => ({
 ...c,
 job,
 stageMessage: stageCopy[job.status] ?? c.stageMessage
 }));
 } catch {}

 unsubscribe = subscribeJobEvents(jobId, {
 onProgress(evt) {
 rotationIdx = 0;
 current.update((c) => ({
 ...c,
 progress: evt.progress,
 stageMessage: evt.stage_message ?? stageCopy[evt.status] ?? c.stageMessage,
 job: c.job ? { ...c.job, status: evt.status } : c.job
 }));
 },
 onDone(status) {
 if (status === 'ready' || status === 'done') {
 current.update((c) => ({ ...c, screen: 'ready', progress: 1 }));
 }
 },
 onError(message) {
 current.update((c) => ({ ...c, screen: 'error', errorMessage: message }));
 }
 });

 rotationTimer = setInterval(() => {
 rotationIdx += 1;
 const st = $current.job?.status ?? 'pending';
 applyRotatingCopy(st);
 }, 10000);
});
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/ProcessingScreen.svelte
git commit -m "feat(frontend): rotate processing copy every 10s to avoid stall feel"
```

---

### Task 11.3: ETA 계산 및 표시

**Files:**
- Modify: `frontend/src/lib/screens/ProcessingScreen.svelte`

진행률만 보여주면 "언제 끝날지" 감을 잡기 어려워 정지감을 준다. 클라이언트 사이드에서 최근 N개의 (시각, 진행률) 샘플로 남은 시간을 간단히 선형 외삽한다.

- [ ] **Step 1: ETA 계산 함수를 script에 추가**

Modify `frontend/src/lib/screens/ProcessingScreen.svelte` script: 아래 상태와 함수 추가.

```typescript
interface Sample {
 t: number;
 p: number;
}
let samples: Sample[] = [];
let etaSec: number | null = null;

function pushSample(progress: number) {
 const t = Date.now();
 samples = [...samples, { t, p: progress }].slice(-6);
 if (samples.length < 2) {
 etaSec = null;
 return;
 }
 const first = samples[0];
 const last = samples[samples.length - 1];
 const dp = last.p - first.p;
 const dt = (last.t - first.t) / 1000;
 if (dp <= 0 || dt <= 0) {
 etaSec = null;
 return;
 }
 const remaining = Math.max(0, 1 - last.p);
 etaSec = Math.round(remaining / (dp / dt));
}

function formatEta(secs: number | null): string | null {
 if (secs == null || !isFinite(secs) || secs < 0) return null;
 if (secs < 60) return `${secs}초 남았어요`;
 const mins = Math.round(secs / 60);
 return `${mins}분 남았어요`;
}
```

`onProgress` 콜백에서 `pushSample(evt.progress)`를 호출. 단계 전환(`status` 변경) 시 `samples = [];`로 리셋하여 다른 단계 속도가 섞이지 않게 한다.

```typescript
onProgress(evt) {
 current.update((c) => {
 if (c.job && c.job.status !== evt.status) {
 samples = [];
 }
 return {
 ...c,
 progress: evt.progress,
 stageMessage: evt.stage_message ?? stageCopy[evt.status] ?? c.stageMessage,
 job: c.job ? { ...c.job, status: evt.status } : c.job
 };
 });
 pushSample(evt.progress);
}
```

- [ ] **Step 2: 템플릿에 ETA 렌더 추가**

`<div class="text-title">{$current.stageMessage}</div>` 바로 아래 삽입:

```svelte
{#if formatEta(etaSec)}
 <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mt-2">
 {formatEta(etaSec)}
 </div>
{/if}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/ProcessingScreen.svelte
git commit -m "feat(frontend): add client-side ETA estimation on processing screen"
```

---
