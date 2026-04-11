# Phase 12 — Ready Screen (Step 3) — Player + Editor

Ready 상태에서 사용자가 영상 시청, 자막 편집, 다운로드를 한 화면에서 할 수 있도록 한다. 이 페이즈는 이 플랜에서 가장 복잡한 UI 페이즈다. 여러 태스크로 쪼개서 단계적으로 쌓는다.

**사전 조건**: Phase 11 완료.

---

### Task 12.1: ReadyScreen 레이아웃 골격

**Files:**
- Create: `frontend/src/lib/screens/ReadyScreen.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: 골격 작성 (영상 영역 + 세그먼트 리스트 placeholder)**

Write `frontend/src/lib/screens/ReadyScreen.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api/jobs';
  import type { JobDto, SegmentDto } from '$lib/api/types';

  export let jobId: string;

  let job: JobDto | null = null;
  let segments: SegmentDto[] = [];
  let loading = true;
  let errorText: string | null = null;

  onMount(async () => {
    try {
      [job, segments] = await Promise.all([api.getJob(jobId), api.segments(jobId)]);
    } catch (e) {
      errorText = e instanceof Error ? e.message : '불러올 수 없어요';
    } finally {
      loading = false;
    }
  });
</script>

<div class="min-h-screen px-6 py-8 max-w-7xl mx-auto">
  {#if loading}
    <div class="text-center text-body">불러오고 있어요...</div>
  {:else if errorText || !job}
    <div class="text-center text-danger">{errorText ?? '데이터 없음'}</div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_420px] gap-8">
      <div class="flex flex-col gap-4">
        <div class="card overflow-hidden aspect-video">
          <!-- 플레이어는 Task 12.2에서 삽입 -->
          <div class="w-full h-full bg-black" />
        </div>
        <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
          {job.duration_sec?.toFixed(0) ?? '?'}초 · {job.language ?? '?'} · {job.model_name} · {segments.length}개 세그먼트
        </div>
      </div>

      <aside class="card p-4 max-h-[calc(100vh-4rem)] overflow-y-auto">
        <div class="text-title mb-4">자막</div>
        <!-- 세그먼트 리스트는 Task 12.3에서 삽입 -->
        <div class="space-y-2">
          {#each segments as seg}
            <div class="p-3 rounded-input">
              <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mb-1">
                {seg.start.toFixed(2)} → {seg.end.toFixed(2)}
              </div>
              <div class="text-body">{seg.text}</div>
            </div>
          {/each}
        </div>
      </aside>
    </div>
  {/if}
</div>
```

- [ ] **Step 2: +page.svelte에서 ReadyScreen 분기**

Modify `frontend/src/routes/+page.svelte`: `$current.screen === 'ready'` 분기에서 ReadyScreen을 import 후 렌더.

Overwrite `frontend/src/routes/+page.svelte`:

```svelte
<script lang="ts">
  import { current } from '$lib/stores/current';
  import IdleScreen from '$lib/screens/IdleScreen.svelte';
  import ProcessingScreen from '$lib/screens/ProcessingScreen.svelte';
  import ReadyScreen from '$lib/screens/ReadyScreen.svelte';

  $: jobId = typeof window !== 'undefined' ? ((window as any).__gensubCurrentJobId as string | undefined) : undefined;
</script>

{#if $current.screen === 'idle'}
  <IdleScreen />
{:else if $current.screen === 'processing' && jobId}
  <ProcessingScreen {jobId} />
{:else if $current.screen === 'ready' && jobId}
  <ReadyScreen {jobId} />
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
git add frontend/src/lib/screens/ReadyScreen.svelte frontend/src/routes/+page.svelte
git commit -m "feat(frontend): add ReadyScreen layout with player and segment list"
```

---

### Task 12.2: 네이티브 <video> + VTT 자막 로드

**Files:**
- Create: `frontend/src/lib/ui/VideoPlayer.svelte`
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte`

- [ ] **Step 1: VideoPlayer 컴포넌트**

Write `frontend/src/lib/ui/VideoPlayer.svelte`:

```svelte
<script lang="ts">
  export let src: string;
  export let vttSrc: string;
  export let currentTime = 0;

  let videoEl: HTMLVideoElement;

  export function seekTo(t: number) {
    if (videoEl) {
      videoEl.currentTime = t;
      videoEl.play().catch(() => {});
    }
  }

  export function togglePlay() {
    if (!videoEl) return;
    if (videoEl.paused) videoEl.play();
    else videoEl.pause();
  }

  function onTimeUpdate() {
    currentTime = videoEl?.currentTime ?? 0;
  }
</script>

<video
  bind:this={videoEl}
  on:timeupdate={onTimeUpdate}
  class="w-full h-full bg-black"
  controls
  preload="metadata"
  crossorigin="anonymous"
>
  <source {src} />
  <track default kind="subtitles" srclang="und" label="자막" src={vttSrc} />
</video>
```

- [ ] **Step 2: ReadyScreen에 플레이어 삽입**

Modify `frontend/src/lib/screens/ReadyScreen.svelte`:

- `<script>` 에 import 추가: `import VideoPlayer from '$lib/ui/VideoPlayer.svelte';`
- `let playerRef: VideoPlayer | null = null;`
- `let currentTime = 0;`
- 영상 영역 `<div class="w-full h-full bg-black" />` 를 아래로 교체:

```svelte
<VideoPlayer
  bind:this={playerRef}
  bind:currentTime
  src={api.videoUrl(jobId)}
  vttSrc={api.vttUrl(jobId)}
/>
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/VideoPlayer.svelte frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "feat(frontend): add VideoPlayer with VTT subtitle track"
```

---

### Task 12.3: 세그먼트 리스트 — 현재 재생 중 하이라이트 + 클릭 점프

**Files:**
- Create: `frontend/src/lib/ui/SegmentList.svelte`
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte`

- [ ] **Step 1: SegmentList 작성**

Write `frontend/src/lib/ui/SegmentList.svelte`:

```svelte
<script lang="ts">
  import { tick } from 'svelte';
  import type { SegmentDto } from '$lib/api/types';

  export let segments: SegmentDto[] = [];
  export let currentTime = 0;
  export let onJump: (t: number) => void = () => {};

  let activeIdx = -1;
  let containerEl: HTMLDivElement;

  $: {
    const i = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);
    if (i !== activeIdx) {
      activeIdx = i;
      tick().then(() => {
        const el = containerEl?.querySelector(`[data-idx="${i}"]`) as HTMLElement | null;
        el?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      });
    }
  }

  function isLowConfidence(seg: SegmentDto): boolean {
    if (seg.avg_logprob == null) return false;
    return seg.avg_logprob < -1.0;
  }
</script>

<div bind:this={containerEl} class="space-y-2">
  {#each segments as seg, i (seg.idx)}
    <button
      type="button"
      data-idx={i}
      on:click={() => onJump(seg.start)}
      class="w-full text-left p-3 rounded-input transition-all
             {activeIdx === i
               ? 'bg-brand/10 border-l-4 border-brand scale-[1.02]'
               : 'hover:bg-divider-light dark:hover:bg-surface-dark-elevated'}
             {isLowConfidence(seg) ? 'bg-warning/10' : ''}"
    >
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mb-1 flex justify-between">
        <span>{seg.start.toFixed(2)} → {seg.end.toFixed(2)}</span>
        {#if seg.edited}
          <span class="text-brand">편집됨</span>
        {/if}
      </div>
      <div class="text-body">{seg.text}</div>
    </button>
  {/each}
</div>
```

- [ ] **Step 2: ReadyScreen에서 SegmentList 사용**

Modify `frontend/src/lib/screens/ReadyScreen.svelte`:

- import: `import SegmentList from '$lib/ui/SegmentList.svelte';`
- aside 내 세그먼트 렌더 부분 교체:

```svelte
<SegmentList
  {segments}
  bind:currentTime
  onJump={(t) => playerRef?.seekTo(t)}
/>
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/SegmentList.svelte frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "feat(frontend): add SegmentList with auto-highlight and click-to-jump"
```

---

### Task 12.4: 인플레이스 텍스트 편집

**Files:**
- Create: `frontend/src/lib/ui/EditableSegment.svelte`
- Modify: `frontend/src/lib/ui/SegmentList.svelte`

- [ ] **Step 1: EditableSegment 컴포넌트**

Write `frontend/src/lib/ui/EditableSegment.svelte`:

```svelte
<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let value: string;
  export let editing = false;

  let inputEl: HTMLSpanElement;
  const dispatch = createEventDispatcher<{ save: string; cancel: void }>();

  $: if (editing && inputEl) {
    setTimeout(() => {
      inputEl.focus();
      const range = document.createRange();
      range.selectNodeContents(inputEl);
      const sel = window.getSelection();
      sel?.removeAllRanges();
      sel?.addRange(range);
    }, 0);
  }

  function commit() {
    const text = inputEl?.innerText?.trim() ?? value;
    dispatch('save', text);
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      dispatch('cancel');
    }
  }
</script>

{#if editing}
  <span
    bind:this={inputEl}
    contenteditable="true"
    class="outline-none ring-2 ring-brand rounded px-1"
    on:keydown={onKey}
    on:blur={commit}
  >{value}</span>
{:else}
  <span>{value}</span>
{/if}
```

- [ ] **Step 2: SegmentList에서 편집 모드 지원**

Modify `frontend/src/lib/ui/SegmentList.svelte`:

- `import EditableSegment from './EditableSegment.svelte';`
- `import { api } from '$lib/api/jobs';`
- `export let jobId: string;`
- `let editingIdx: number | null = null;`
- 세그먼트 텍스트 클릭 시 편집 모드 진입:

```svelte
{#if editingIdx === i}
  <EditableSegment
    value={seg.text}
    editing={true}
    on:save={async (e) => {
      editingIdx = null;
      try {
        await api.patchSegment(jobId, seg.idx, { text: e.detail });
        segments[i] = { ...seg, text: e.detail, edited: true };
      } catch {}
    }}
    on:cancel={() => (editingIdx = null)}
  />
{:else}
  <span
    class="text-body cursor-text"
    on:dblclick|stopPropagation={() => (editingIdx = i)}
  >{seg.text}</span>
{/if}
```

(단순화를 위해 SegmentList의 button을 div로 바꾸고, 헤더 영역(시간표시)만 클릭 시 점프, 텍스트는 더블클릭으로 편집하도록 수정한다.)

이 수정을 적용하려면 SegmentList의 `<button>` 요소를 다음 구조로 변경:

```svelte
<div
  data-idx={i}
  class="w-full text-left p-3 rounded-input transition-all
         {activeIdx === i
           ? 'bg-brand/10 border-l-4 border-brand scale-[1.02]'
           : 'hover:bg-divider-light dark:hover:bg-surface-dark-elevated'}
         {isLowConfidence(seg) ? 'bg-warning/10' : ''}"
>
  <button
    type="button"
    on:click={() => onJump(seg.start)}
    class="w-full text-left text-caption text-text-secondary-light dark:text-text-secondary-dark mb-1 flex justify-between"
  >
    <span>{seg.start.toFixed(2)} → {seg.end.toFixed(2)}</span>
    {#if seg.edited}
      <span class="text-brand">편집됨</span>
    {/if}
  </button>
  {#if editingIdx === i}
    <EditableSegment
      value={seg.text}
      editing={true}
      on:save={async (e) => {
        editingIdx = null;
        try {
          await api.patchSegment(jobId, seg.idx, { text: e.detail });
          segments[i] = { ...seg, text: e.detail, edited: true };
        } catch {}
      }}
      on:cancel={() => (editingIdx = null)}
    />
  {:else}
    <span
      class="text-body cursor-text block"
      on:dblclick|stopPropagation={() => (editingIdx = i)}
    >{seg.text}</span>
  {/if}
</div>
```

- [ ] **Step 3: ReadyScreen에서 jobId를 SegmentList에 전달**

Modify `frontend/src/lib/screens/ReadyScreen.svelte`:

```svelte
<SegmentList {jobId} {segments} bind:currentTime onJump={(t) => playerRef?.seekTo(t)} />
```

- [ ] **Step 4: 빌드 확인**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/EditableSegment.svelte frontend/src/lib/ui/SegmentList.svelte frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "feat(frontend): inline segment editing via double-click"
```

---

### Task 12.5: 타이밍 미세 조정 + 재전사 버튼

**Files:**
- Modify: `frontend/src/lib/ui/SegmentList.svelte`

- [ ] **Step 1: 각 세그먼트에 타이밍/재전사 액션 추가**

Modify `SegmentList.svelte`: 세그먼트 div 하단에 아래 컨트롤 삽입 (editingIdx === i 가 아닐 때만).

```svelte
{#if activeIdx === i}
  <div class="flex gap-2 mt-2 text-caption">
    <button
      type="button"
      class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
      on:click={async () => {
        const next = Math.max(0, seg.start - 0.1);
        await api.patchSegment(jobId, seg.idx, { start: next });
        segments[i] = { ...seg, start: next };
      }}
    >시작 −0.1</button>
    <button
      type="button"
      class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
      on:click={async () => {
        const next = seg.start + 0.1;
        await api.patchSegment(jobId, seg.idx, { start: next });
        segments[i] = { ...seg, start: next };
      }}
    >시작 +0.1</button>
    <button
      type="button"
      class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
      on:click={async () => {
        const next = Math.max(seg.start + 0.1, seg.end - 0.1);
        await api.patchSegment(jobId, seg.idx, { end: next });
        segments[i] = { ...seg, end: next };
      }}
    >끝 −0.1</button>
    <button
      type="button"
      class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
      on:click={async () => {
        const next = seg.end + 0.1;
        await api.patchSegment(jobId, seg.idx, { end: next });
        segments[i] = { ...seg, end: next };
      }}
    >끝 +0.1</button>
    <button
      type="button"
      class="ml-auto px-2 py-1 rounded bg-brand text-white"
      on:click={async () => {
        try {
          await api.regenerateSegment(jobId, seg.idx);
          // refetch all segments
          segments = await api.segments(jobId);
        } catch {}
      }}
    >↻ 재전사</button>
  </div>
{/if}
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/SegmentList.svelte
git commit -m "feat(frontend): add timing adjust and re-transcribe buttons"
```

---

### Task 12.6: 다운로드 바 + 찾아 바꾸기 패널

**Files:**
- Create: `frontend/src/lib/ui/DownloadBar.svelte`
- Create: `frontend/src/lib/ui/SearchReplace.svelte`
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte`

- [ ] **Step 1: DownloadBar**

Write `frontend/src/lib/ui/DownloadBar.svelte`:

```svelte
<script lang="ts">
  import { api } from '$lib/api/jobs';
  import Button from '$lib/ui/Button.svelte';
  export let jobId: string;
  export let onBurnClick: () => void = () => {};
</script>

<div class="flex flex-wrap items-center gap-2">
  <a
    class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
    href={api.srtUrl(jobId)}
    download
  >.srt</a>
  <a
    class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
    href={api.vttUrl(jobId)}
    download
  >.vtt</a>
  <a
    class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
    href={api.txtUrl(jobId)}
    download
  >.txt</a>
  <a
    class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
    href={api.jsonUrl(jobId)}
    download
  >.json</a>
  <a
    class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
    href={api.mkvUrl(jobId)}
    download
  >.mkv</a>
  <div class="ml-auto">
    <Button variant="primary" on:click={onBurnClick}>
      🔥 영상에 구워서 다운로드
    </Button>
  </div>
</div>
```

- [ ] **Step 2: SearchReplace 패널**

Write `frontend/src/lib/ui/SearchReplace.svelte`:

```svelte
<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { api } from '$lib/api/jobs';
  import Button from '$lib/ui/Button.svelte';

  export let jobId: string;
  let find = '';
  let replaceText = '';
  let caseSensitive = false;
  let lastChanged: number | null = null;

  const dispatch = createEventDispatcher<{ applied: void }>();

  async function run() {
    if (!find.trim()) return;
    try {
      const res = await api.searchReplace(jobId, find, replaceText, caseSensitive);
      lastChanged = res.changed_count;
      if (res.changed_count > 0) dispatch('applied');
    } catch {}
  }
</script>

<div class="card p-4 flex flex-col gap-3">
  <div class="flex items-center gap-2">
    <input
      class="flex-1 px-3 py-2 bg-divider-light dark:bg-surface-dark-elevated rounded-input text-body"
      placeholder="찾을 단어"
      bind:value={find}
    />
    <input
      class="flex-1 px-3 py-2 bg-divider-light dark:bg-surface-dark-elevated rounded-input text-body"
      placeholder="바꿀 단어"
      bind:value={replaceText}
    />
  </div>
  <label class="text-caption flex items-center gap-2">
    <input type="checkbox" bind:checked={caseSensitive} />
    대소문자 구분
  </label>
  <div class="flex items-center gap-3">
    <Button variant="primary" on:click={run}>모두 바꾸기</Button>
    {#if lastChanged !== null}
      <span class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
        {lastChanged}개 세그먼트를 변경했어요
      </span>
    {/if}
  </div>
</div>
```

- [ ] **Step 3: ReadyScreen에 통합**

Modify `frontend/src/lib/screens/ReadyScreen.svelte`:

- import: `import DownloadBar from '$lib/ui/DownloadBar.svelte';`
- import: `import SearchReplace from '$lib/ui/SearchReplace.svelte';`
- `let showSearch = false;`
- `let showBurnSheet = false;`
- 영상 컬럼 하단에 DownloadBar 배치:

```svelte
<DownloadBar {jobId} onBurnClick={() => (showBurnSheet = true)} />
```

- aside 상단에 SearchReplace 토글:

```svelte
<div class="mb-3">
  <button
    class="text-caption text-brand"
    on:click={() => (showSearch = !showSearch)}
  >🔍 찾아 바꾸기</button>
</div>
{#if showSearch}
  <div class="mb-4">
    <SearchReplace
      {jobId}
      on:applied={async () => {
        segments = await api.segments(jobId);
      }}
    />
  </div>
{/if}
```

- [ ] **Step 4: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/DownloadBar.svelte frontend/src/lib/ui/SearchReplace.svelte frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "feat(frontend): add DownloadBar and SearchReplace panel"
```

---

### Task 12.7: 키보드 단축키

**Files:**
- Create: `frontend/src/lib/screens/useShortcuts.ts`
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte`

- [ ] **Step 1: 단축키 핸들러 유틸**

Write `frontend/src/lib/screens/useShortcuts.ts`:

```typescript
export interface ShortcutHandlers {
  togglePlay: () => void;
  prevSegment: () => void;
  nextSegment: () => void;
  seekRelative: (delta: number) => void;
  regenerateCurrent: () => void;
  toggleSearch: () => void;
}

export function installShortcuts(handlers: ShortcutHandlers): () => void {
  function onKey(e: KeyboardEvent) {
    const target = e.target as HTMLElement | null;
    if (target && (target.tagName === 'INPUT' || target.isContentEditable)) {
      return;
    }
    switch (e.key) {
      case ' ':
        e.preventDefault();
        handlers.togglePlay();
        break;
      case 'ArrowUp':
        e.preventDefault();
        handlers.prevSegment();
        break;
      case 'ArrowDown':
        e.preventDefault();
        handlers.nextSegment();
        break;
      case 'j':
        handlers.seekRelative(-5);
        break;
      case 'l':
        handlers.seekRelative(5);
        break;
      case 'r':
      case 'R':
        handlers.regenerateCurrent();
        break;
      default:
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') {
          e.preventDefault();
          handlers.toggleSearch();
        }
    }
  }
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}
```

- [ ] **Step 2: ReadyScreen 훅 연결**

Modify `frontend/src/lib/screens/ReadyScreen.svelte` script:

```typescript
import { installShortcuts } from './useShortcuts';

let unshort: (() => void) | null = null;

onMount(() => {
  unshort = installShortcuts({
    togglePlay: () => playerRef?.togglePlay(),
    prevSegment: () => {
      const i = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);
      if (i > 0) playerRef?.seekTo(segments[i - 1].start);
    },
    nextSegment: () => {
      const i = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);
      if (i >= 0 && i < segments.length - 1) playerRef?.seekTo(segments[i + 1].start);
    },
    seekRelative: (d) => {
      const t = Math.max(0, currentTime + d);
      playerRef?.seekTo(t);
    },
    regenerateCurrent: async () => {
      const i = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);
      if (i < 0) return;
      try {
        await api.regenerateSegment(jobId, segments[i].idx);
        segments = await api.segments(jobId);
      } catch {}
    },
    toggleSearch: () => (showSearch = !showSearch)
  });
});

onDestroy(() => {
  unshort?.();
});
```

(필요 시 `onMount`/`onDestroy` import 추가.)

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/useShortcuts.ts frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "feat(frontend): add keyboard shortcuts for player and editor"
```

---
