# Phase 14 — Header + Recent Jobs + Error Polish

자잘한 마감 요소를 마무리한다. 헤더(다크모드 토글, 최근 작업 버튼), 최근 작업 패널, 에러 화면 폴리시.

**사전 조건**: Phase 13 완료.

---

### Task 14.1: Header 컴포넌트 (테마 토글 + 최근 버튼)

**Files:**
- Create: `frontend/src/lib/ui/Header.svelte`
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: Header 작성**

Write `frontend/src/lib/ui/Header.svelte`:

```svelte
<script lang="ts">
 import { theme, toggleTheme } from '$lib/theme';
 import { Moon, Sun, History } from 'lucide-svelte';

 export let onRecentClick: () => void = () => {};
</script>

<header class="fixed top-0 inset-x-0 z-30 flex items-center justify-between px-6 py-4 backdrop-blur">
 <div class="text-title tracking-tight">GenSub</div>
 <div class="flex items-center gap-2">
 <button
 type="button"
 on:click={onRecentClick}
 class="p-2 rounded-full hover:bg-divider-light dark:hover:bg-surface-dark-elevated"
 aria-label="최근 작업"
 >
 <History size={20} />
 </button>
 <button
 type="button"
 on:click={toggleTheme}
 class="p-2 rounded-full hover:bg-divider-light dark:hover:bg-surface-dark-elevated"
 aria-label="다크 모드 전환"
 >
 {#if $theme === 'dark'}
 <Sun size={20} />
 {:else}
 <Moon size={20} />
 {/if}
 </button>
 </div>
</header>
```

- [ ] **Step 2: layout에 Header + 상태 배치**

Overwrite `frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
 import '../app.css';
 import { onMount } from 'svelte';
 import { initTheme } from '$lib/theme';
 import { initHistory } from '$lib/stores/history';
 import Header from '$lib/ui/Header.svelte';

 let recentOpen = false;

 onMount(() => {
 initTheme();
 initHistory();
 });
</script>

<Header onRecentClick={() => (recentOpen = !recentOpen)} />

<main class="pt-16">
 <slot />
</main>

<!-- recentOpen 패널은 Task 14.2에서 구현 -->
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/Header.svelte frontend/src/routes/+layout.svelte
git commit -m "feat(frontend): add Header with theme toggle and recent button"
```

---

### Task 14.2: 최근 작업 패널

**Files:**
- Create: `frontend/src/lib/ui/RecentPanel.svelte`
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: RecentPanel 작성**

Write `frontend/src/lib/ui/RecentPanel.svelte`:

```svelte
<script lang="ts">
 import { fly, fade } from 'svelte/transition';
 import { cubicOut } from 'svelte/easing';
 import { history, removeFromHistory } from '$lib/stores/history';
 import { current } from '$lib/stores/current';

 export let open = false;
 export let onClose: () => void = () => {};

 function openJob(jobId: string) {
 (window as any).__gensubCurrentJobId = jobId;
 current.set({
 screen: 'ready',
 job: null,
 progress: 1,
 stageMessage: '',
 errorMessage: null
 });
 onClose();
 }
</script>

{#if open}
 <div class="fixed inset-0 z-40 bg-black/30" on:click={onClose} transition:fade={{ duration: 200 }} />
 <aside
 class="fixed top-0 right-0 bottom-0 z-50 w-[360px] bg-surface-light dark:bg-surface-dark
 shadow-card p-6 overflow-y-auto"
 transition:fly={{ x: 400, duration: 380, easing: cubicOut }}
 >
 <div class="text-title mb-6">최근 작업</div>
 {#if $history.length === 0}
 <div class="text-body text-text-secondary-light dark:text-text-secondary-dark">
 아직 처리한 영상이 없어요
 </div>
 {:else}
 <div class="flex flex-col gap-3">
 {#each $history as item}
 <div class="card p-3 flex items-center gap-3">
 <button
 type="button"
 class="flex-1 text-left"
 on:click={() => openJob(item.jobId)}
 >
 <div class="text-body truncate">{item.title ?? item.jobId}</div>
 <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
 {new Date(item.createdAt).toLocaleString('ko-KR')}
 </div>
 </button>
 <button
 type="button"
 class="text-caption text-danger"
 on:click={() => removeFromHistory(item.jobId)}
 aria-label="삭제"
 >×</button>
 </div>
 {/each}
 </div>
 {/if}
 </aside>
{/if}
```

- [ ] **Step 2: layout에서 RecentPanel 렌더**

Overwrite `frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
 import '../app.css';
 import { onMount } from 'svelte';
 import { initTheme } from '$lib/theme';
 import { initHistory } from '$lib/stores/history';
 import Header from '$lib/ui/Header.svelte';
 import RecentPanel from '$lib/ui/RecentPanel.svelte';

 let recentOpen = false;

 onMount(() => {
 initTheme();
 initHistory();
 });
</script>

<Header onRecentClick={() => (recentOpen = true)} />

<main class="pt-16">
 <slot />
</main>

<RecentPanel open={recentOpen} onClose={() => (recentOpen = false)} />
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/RecentPanel.svelte frontend/src/routes/+layout.svelte
git commit -m "feat(frontend): add RecentPanel with localStorage history"
```

---

### Task 14.3: 에러 화면 개선

**Files:**
- Create: `frontend/src/lib/screens/ErrorScreen.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: 전용 ErrorScreen**

Write `frontend/src/lib/screens/ErrorScreen.svelte`:

```svelte
<script lang="ts">
 import Button from '$lib/ui/Button.svelte';
 import { current, reset } from '$lib/stores/current';

 let detailsOpen = false;
</script>

<div class="min-h-screen flex items-center justify-center px-6">
 <div class="max-w-md flex flex-col items-center gap-6 text-center">
 <div class="text-display">문제가 생겼어요</div>
 <div class="text-body text-text-secondary-light dark:text-text-secondary-dark">
 {$current.errorMessage ?? '알 수 없는 오류'}
 </div>
 <Button variant="primary" on:click={reset}>다시 시도하기</Button>
 <button
 type="button"
 class="text-caption text-text-secondary-light dark:text-text-secondary-dark underline"
 on:click={() => (detailsOpen = !detailsOpen)}
 >
 {detailsOpen ? '자세히 숨기기' : '자세히 보기'}
 </button>
 {#if detailsOpen}
 <pre class="text-caption text-left bg-divider-light dark:bg-surface-dark-elevated p-3 rounded-input max-w-full overflow-auto">
{$current.errorMessage}
 </pre>
 {/if}
 </div>
</div>
```

- [ ] **Step 2: +page.svelte에서 ErrorScreen 사용**

Modify `frontend/src/routes/+page.svelte`: import 추가 및 `error` 분기에서 ErrorScreen 사용.

```svelte
<script lang="ts">
 import { current } from '$lib/stores/current';
 import IdleScreen from '$lib/screens/IdleScreen.svelte';
 import ProcessingScreen from '$lib/screens/ProcessingScreen.svelte';
 import ReadyScreen from '$lib/screens/ReadyScreen.svelte';
 import BurnDoneScreen from '$lib/screens/BurnDoneScreen.svelte';
 import ErrorScreen from '$lib/screens/ErrorScreen.svelte';

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
 <ErrorScreen />
{/if}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/ErrorScreen.svelte frontend/src/routes/+page.svelte
git commit -m "feat(frontend): add dedicated ErrorScreen with details toggle"
```

---
