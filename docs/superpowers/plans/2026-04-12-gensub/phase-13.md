# Phase 13 — Burn-in Bottom Sheet (Step 4)

iOS 스타일 bottom sheet 모달로 burn-in 옵션을 고르고 작업을 트리거한다.

**사전 조건**: Phase 12 완료.

---

### Task 13.1: BottomSheet 컨테이너

**Files:**
- Create: `frontend/src/lib/ui/BottomSheet.svelte`

- [ ] **Step 1: 작성**

Write `frontend/src/lib/ui/BottomSheet.svelte`:

```svelte
<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';

  export let open = false;
  export let onClose: () => void = () => {};
</script>

{#if open}
  <div
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
    on:click={onClose}
    transition:fade={{ duration: 200 }}
  />
  <div
    class="fixed inset-x-0 bottom-0 z-50 bg-surface-light dark:bg-surface-dark
           rounded-t-[28px] shadow-card pb-6"
    transition:fly={{ y: 400, duration: 380, easing: cubicOut }}
  >
    <div class="flex justify-center pt-3 pb-1">
      <div class="w-10 h-1.5 rounded-full bg-divider-light dark:bg-divider-dark" />
    </div>
    <div class="px-6 pt-2">
      <slot />
    </div>
  </div>
{/if}
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/BottomSheet.svelte
git commit -m "feat(frontend): add BottomSheet modal with fly-in spring"
```

---

### Task 13.2: Burn 옵션 시트

**Files:**
- Create: `frontend/src/lib/ui/BurnSheet.svelte`
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte`

- [ ] **Step 1: BurnSheet 작성**

Write `frontend/src/lib/ui/BurnSheet.svelte`:

```svelte
<script lang="ts">
  import Button from '$lib/ui/Button.svelte';
  import Segmented from '$lib/ui/Segmented.svelte';
  import BottomSheet from '$lib/ui/BottomSheet.svelte';
  import { api } from '$lib/api/jobs';
  import { current } from '$lib/stores/current';

  export let open = false;
  export let jobId: string;
  export let onClose: () => void = () => {};

  let size: '32' | '42' | '54' = '42';
  let outline = true;

  const sizeOptions = [
    { value: '32', label: '작게' },
    { value: '42', label: '중간' },
    { value: '54', label: '크게' }
  ];

  async function start() {
    try {
      await api.triggerBurn(jobId, { size: parseInt(size, 10), outline });
      onClose();
      current.set({
        screen: 'processing',
        job: null,
        progress: 0,
        stageMessage: '자막을 영상에 입히고 있어요',
        errorMessage: null
      });
    } catch {}
  }
</script>

<BottomSheet {open} {onClose}>
  <div class="flex flex-col gap-6 py-2">
    <div>
      <div class="text-title">자막을 영상에 입힐게요</div>
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mt-1">
        영상 길이에 따라 수 분 정도 걸려요
      </div>
    </div>

    <div class="flex items-center justify-between">
      <span class="text-body">크기</span>
      <Segmented options={sizeOptions} bind:value={size} />
    </div>

    <label class="flex items-center justify-between text-body">
      <span>외곽선</span>
      <input type="checkbox" bind:checked={outline} class="w-12 h-7 rounded-full" />
    </label>

    <Button variant="primary" fullWidth on:click={start}>시작하기</Button>
    <Button variant="ghost" fullWidth on:click={onClose}>취소</Button>
  </div>
</BottomSheet>
```

- [ ] **Step 2: ReadyScreen에 연결**

Modify `frontend/src/lib/screens/ReadyScreen.svelte`:

- import: `import BurnSheet from '$lib/ui/BurnSheet.svelte';`
- 기존 `let showBurnSheet = false;` 유지
- JSX 최하단(또는 루트 div 하단)에 다음 추가:

```svelte
<BurnSheet
  open={showBurnSheet}
  {jobId}
  onClose={() => (showBurnSheet = false)}
/>
```

DownloadBar의 `onBurnClick`이 이미 `showBurnSheet = true`로 되어 있으면 OK.

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/BurnSheet.svelte frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "feat(frontend): add BurnSheet with style options"
```

---

### Task 13.3: Burn 완료 후 다운로드 링크

**Files:**
- Modify: `frontend/src/lib/screens/ProcessingScreen.svelte`
- Create: `frontend/src/lib/screens/BurnDoneScreen.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: BurnDoneScreen 작성**

Write `frontend/src/lib/screens/BurnDoneScreen.svelte`:

```svelte
<script lang="ts">
  import { api } from '$lib/api/jobs';
  import Button from '$lib/ui/Button.svelte';
  import { current } from '$lib/stores/current';

  export let jobId: string;
</script>

<div class="min-h-screen flex items-center justify-center px-6">
  <div class="max-w-md flex flex-col items-center gap-8 text-center">
    <div class="text-display">완료됐어요</div>
    <div class="text-body text-text-secondary-light dark:text-text-secondary-dark">
      자막이 영상에 입혀진 mp4 파일이 준비됐어요
    </div>
    <a class="w-full" href={api.burnedUrl(jobId)} download>
      <Button variant="primary" fullWidth>다운로드</Button>
    </a>
    <Button
      variant="ghost"
      on:click={() => current.update((c) => ({ ...c, screen: 'ready' }))}
    >편집기로 돌아가기</Button>
  </div>
</div>
```

- [ ] **Step 2: ProcessingScreen에서 done 상태 분기**

Modify `frontend/src/lib/screens/ProcessingScreen.svelte`: `onDone` 핸들러가 status가 `done`이면 current.screen을 `burn_done`으로 설정하도록 수정.

기존:
```typescript
onDone(status) {
  if (status === 'ready' || status === 'done') {
    current.update((c) => ({ ...c, screen: 'ready', progress: 1 }));
  }
}
```

교체:
```typescript
onDone(status) {
  if (status === 'done') {
    current.update((c) => ({ ...c, screen: 'burn_done', progress: 1 }));
  } else if (status === 'ready') {
    current.update((c) => ({ ...c, screen: 'ready', progress: 1 }));
  }
}
```

- [ ] **Step 3: current 스토어 타입 확장**

Modify `frontend/src/lib/stores/current.ts`:

```typescript
export type Screen = 'idle' | 'processing' | 'ready' | 'burn_done' | 'error';
```

- [ ] **Step 4: +page.svelte에 분기 추가**

Modify `frontend/src/routes/+page.svelte`:

```svelte
<script lang="ts">
  import { current } from '$lib/stores/current';
  import IdleScreen from '$lib/screens/IdleScreen.svelte';
  import ProcessingScreen from '$lib/screens/ProcessingScreen.svelte';
  import ReadyScreen from '$lib/screens/ReadyScreen.svelte';
  import BurnDoneScreen from '$lib/screens/BurnDoneScreen.svelte';

  $: jobId = typeof window !== 'undefined' ? ((window as any).__gensubCurrentJobId as string | undefined) : undefined;
</script>

{#if $current.screen === 'idle'}
  <IdleScreen />
{:else if $current.screen === 'processing' && jobId}
  <ProcessingScreen {jobId} />
{:else if $current.screen === 'ready' && jobId}
  <ReadyScreen {jobId} />
{:else if $current.screen === 'burn_done' && jobId}
  <BurnDoneScreen {jobId} />
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

- [ ] **Step 5: 빌드 확인**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 6: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/BurnDoneScreen.svelte frontend/src/lib/screens/ProcessingScreen.svelte frontend/src/lib/stores/current.ts frontend/src/routes/+page.svelte
git commit -m "feat(frontend): add BurnDoneScreen and transitions"
```

---
