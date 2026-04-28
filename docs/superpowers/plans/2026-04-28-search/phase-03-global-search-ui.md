# Phase 3 — Frontend: 헤더 SearchBar + 글로벌 SearchModal + ⌘K

목표: 항상 보이는 헤더 검색바 + ⌘K 단축키 + 모달 결과 리스트.

**전제**: Phase 2 완료, `feature/search` 브랜치.

---

### Task 3.1: SearchBar 컴포넌트 (헤더 visible bar)

**Files:**
- Create: `frontend/src/lib/ui/SearchBar.svelte`

- [ ] **Step 1: 기존 컴포넌트 스타일 참고**

```bash
cd /Users/loki/GenSub
head -30 frontend/src/lib/ui/Input.svelte 2>/dev/null || true
grep -l "rounded-input\|bg-surface" frontend/src/lib/ui/*.svelte | head
```

기존 input 스타일 톤을 맞추기 위함.

- [ ] **Step 2: SearchBar 작성**

Write `frontend/src/lib/ui/SearchBar.svelte`:

```svelte
<script lang="ts">
  import { Search } from 'lucide-svelte';

  import { searchOpen, searchQuery } from '$lib/stores/search';

  function handleClick() {
    searchOpen.set(true);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      searchOpen.set(true);
    }
  }
</script>

<button
  type="button"
  on:click={handleClick}
  on:keydown={handleKey}
  class="flex items-center gap-2 w-full max-w-[360px]
         h-9 px-3 rounded-xl
         bg-black/[0.04] dark:bg-white/[0.06]
         hover:bg-black/[0.06] dark:hover:bg-white/[0.08]
         text-text-secondary-light dark:text-text-secondary-dark
         text-[13px] transition-colors text-left"
  aria-label="검색 열기"
>
  <Search size={15} strokeWidth={1.75} />
  <span class="flex-1 truncate">
    {#if $searchQuery}
      {$searchQuery}
    {:else}
      자막·메모·영상 검색…
    {/if}
  </span>
  <kbd class="hidden sm:inline-flex text-[10px] px-1.5 py-0.5 rounded
              border border-black/[0.08] dark:border-white/[0.1]
              text-text-secondary-light dark:text-text-secondary-dark">
    ⌘K
  </kbd>
</button>
```

- [ ] **Step 3: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/SearchBar.svelte
git commit -m "feat(search): add SearchBar component (header visible)

스펙 §5.2: 헤더에 항상 보이는 검색 진입점.
- max-w 360px, 좌측 search 아이콘
- 클릭/Enter → searchOpen 스토어 set true (모달 열기)
- 우측에 ⌘K 단축키 표시 (sm 이상)
- 입력값은 stores/search.searchQuery 와 동기화 (모달이 진짜 입력 처리)"
```

---

### Task 3.2: SearchModal 컴포넌트

**Files:**
- Create: `frontend/src/lib/ui/SearchModal.svelte`

- [ ] **Step 1: 모달 작성**

Write `frontend/src/lib/ui/SearchModal.svelte`:

```svelte
<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Search, FileVideo, Bookmark, MessageSquare, Loader2 } from 'lucide-svelte';

  import type { SearchHit } from '$lib/api/types';
  import { openMemo } from '$lib/stores/current';
  import {
    closeSearch,
    scheduleSearch,
    searchLoading,
    searchOpen,
    searchQuery,
    searchResults,
  } from '$lib/stores/search';

  let inputEl: HTMLInputElement | null = null;

  // open 될 때 자동 포커스
  $: if ($searchOpen && inputEl) {
    queueMicrotask(() => inputEl?.focus());
  }

  // query 변경 시 debounce 검색
  $: scheduleSearch($searchQuery);

  function handleBackdrop() {
    closeSearch();
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      closeSearch();
    }
  }

  function handleResultClick(hit: SearchHit) {
    openMemo(hit.job_id, hit.start ?? 0);
    closeSearch();
  }

  function fmtMMSS(sec: number | undefined): string {
    if (sec === undefined) return '';
    const total = Math.floor(sec);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function previewText(hit: SearchHit): string {
    if (hit.kind === 'memo') return hit.memo_text || hit.segment_text || '';
    if (hit.kind === 'segment') return hit.segment_text || '';
    return hit.job_title || '';
  }

  onDestroy(() => {
    // store는 보존, listener만 정리
  });
</script>

{#if $searchOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
    on:click={handleBackdrop}
    on:keydown={handleKey}
  >
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      class="fixed left-1/2 top-16 -translate-x-1/2 w-[min(640px,calc(100vw-32px))]
             max-h-[min(500px,calc(100vh-128px))]
             bg-white dark:bg-[#1c1c1e]
             rounded-2xl shadow-2xl border border-black/[0.06] dark:border-white/[0.06]
             flex flex-col overflow-hidden"
      on:click|stopPropagation
    >
      <!-- 입력창 -->
      <div class="flex items-center gap-3 px-4 h-14 border-b border-black/[0.06] dark:border-white/[0.06]">
        <Search size={18} strokeWidth={1.75}
                class="text-text-secondary-light dark:text-text-secondary-dark shrink-0" />
        <input
          bind:this={inputEl}
          bind:value={$searchQuery}
          on:keydown={handleKey}
          type="text"
          placeholder="자막·메모·영상 검색…"
          class="flex-1 bg-transparent border-0 outline-none
                 text-body text-text-primary-light dark:text-text-primary-dark
                 placeholder:text-text-secondary-light dark:placeholder:text-text-secondary-dark"
        />
        {#if $searchLoading}
          <Loader2 size={16} class="animate-spin text-text-secondary-light dark:text-text-secondary-dark" />
        {/if}
        <button
          type="button"
          on:click={closeSearch}
          class="text-[11px] px-1.5 py-0.5 rounded
                 border border-black/[0.08] dark:border-white/[0.1]
                 text-text-secondary-light dark:text-text-secondary-dark
                 hover:bg-black/[0.04] dark:hover:bg-white/[0.06]"
        >
          Esc
        </button>
      </div>

      <!-- 결과 -->
      <div class="flex-1 overflow-y-auto">
        {#if $searchQuery.trim() === ''}
          <div class="px-6 py-12 text-center text-[13px]
                      text-text-secondary-light dark:text-text-secondary-dark">
            검색어를 입력하세요.
            <br />
            영상 제목 · 메모 · 자막 모두 검색합니다.
          </div>
        {:else if $searchResults.length === 0 && !$searchLoading}
          <div class="px-6 py-12 text-center text-[13px]
                      text-text-secondary-light dark:text-text-secondary-dark">
            결과가 없어요.
          </div>
        {:else}
          <ul class="py-2">
            {#each $searchResults as hit (hit.kind + '-' + (hit.memo_id ?? hit.segment_idx ?? hit.job_id))}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
              <li
                role="button"
                tabindex="0"
                class="flex items-start gap-3 px-4 py-2.5
                       hover:bg-black/[0.04] dark:hover:bg-white/[0.04]
                       cursor-pointer transition-colors"
                on:click={() => handleResultClick(hit)}
                on:keydown={(e) => e.key === 'Enter' && handleResultClick(hit)}
              >
                <span class="shrink-0 pt-0.5
                             text-text-secondary-light dark:text-text-secondary-dark">
                  {#if hit.kind === 'job'}
                    <FileVideo size={14} strokeWidth={1.75} />
                  {:else if hit.kind === 'memo'}
                    <Bookmark size={14} strokeWidth={1.75} />
                  {:else}
                    <MessageSquare size={14} strokeWidth={1.75} />
                  {/if}
                </span>
                <div class="flex-1 min-w-0">
                  <div class="text-[13px] leading-snug
                              text-text-primary-light dark:text-text-primary-dark
                              line-clamp-2">
                    {previewText(hit)}
                  </div>
                  <div class="mt-0.5 text-[11px]
                              text-text-secondary-light dark:text-text-secondary-dark
                              flex items-center gap-1.5">
                    {#if hit.kind !== 'job'}
                      <span class="truncate">{hit.job_title ?? '(제목 없음)'}</span>
                      <span>·</span>
                      <span class="tabular-nums shrink-0">{fmtMMSS(hit.start)}</span>
                    {:else}
                      <span class="opacity-70">영상</span>
                    {/if}
                  </div>
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  </div>
{/if}
```

- [ ] **Step 2: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -10
```

Expected: 0 errors.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/SearchModal.svelte
git commit -m "feat(search): add SearchModal component

스펙 §5.4: ⌘K 또는 헤더 SearchBar 클릭으로 열리는 모달.
- 화면 중앙, max 640×500, top 64px offset
- 백드롭 dim+blur, 외부 클릭/Esc 로 닫힘
- 자동 포커스, 입력 → debounce 200ms → /api/search
- 결과 카드 3종 아이콘 (FileVideo / Bookmark / MessageSquare)
- 결과 클릭 → openMemo(job_id, start) → 모달 닫힘
- 빈 query / 결과 없음 / 로딩 상태 분기 표시"
```

---

### Task 3.3: +layout.svelte에 SearchBar + ⌘K 통합

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: 현재 layout 확인**

```bash
cd /Users/loki/GenSub
cat frontend/src/routes/+layout.svelte
```

기존 헤더 구조 (다크모드 토글, 사이드바 토글) 확인.

- [ ] **Step 2: SearchBar + SearchModal import + ⌘K 핸들러**

Edit `frontend/src/routes/+layout.svelte`:

`<script>` 상단 import에 추가:

```ts
import SearchBar from '$lib/ui/SearchBar.svelte';
import SearchModal from '$lib/ui/SearchModal.svelte';
import { searchOpen } from '$lib/stores/search';
```

`onMount` 안에 글로벌 keydown 리스너 추가 (cleanup 포함):

```ts
function handleGlobalKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    searchOpen.set(true);
  }
}

onMount(() => {
  initTheme();
  initHistory();
  if (typeof window !== 'undefined' && window.innerWidth < 768) {
    sidebarCollapsed = true;
  }
  window.addEventListener('keydown', handleGlobalKey);
  return () => window.removeEventListener('keydown', handleGlobalKey);
});
```

(기존 onMount가 cleanup return을 안 하던 형태면, 위처럼 return 추가.)

`<header>` 영역에 SearchBar 삽입. 기존 헤더 구조에 따라 다음과 같이:

```svelte
<header
  class="fixed top-0 z-10 flex items-center gap-3 px-5 h-14 transition-all duration-300 ease-spring
         {sidebarCollapsed ? 'left-0' : 'left-[260px]'} right-0"
>
  <div class="flex items-center gap-2 shrink-0">
    {#if sidebarCollapsed}
      <button ...>...</button>
      <span class="text-body font-bold tracking-tight">GenSub</span>
    {/if}
  </div>

  <!-- SearchBar 가운데 영역 -->
  <div class="flex-1 flex justify-center">
    <SearchBar />
  </div>

  <button
    type="button"
    on:click={toggleTheme}
    class="..."
    aria-label="다크 모드 전환"
  >
    ...
  </button>
</header>
```

기존 헤더의 정확한 구조에 맞춰 `<div class="flex-1 flex justify-center"><SearchBar /></div>` 삽입 위치 조정.

`<main>` 끝나는 곳 또는 `<header>` 끝난 직후에 `<SearchModal />` 추가:

```svelte
<main ...>
  <slot />
</main>

<SearchModal />
```

- [ ] **Step 3: 타입체크 + 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -10
npm run build 2>&1 | tail -5
```

Expected: 0 errors, 빌드 성공.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/routes/+layout.svelte
git commit -m "feat(search): wire SearchBar/SearchModal + ⌘K into layout

스펙 §5.3:
- 헤더 가운데 영역에 <SearchBar /> (항상 visible)
- 페이지 끝에 <SearchModal />
- onMount 에서 window keydown 리스너로 ⌘K/Ctrl+K 캡처
- onMount cleanup 으로 listener 해제

이제 어디서든 ⌘K 또는 헤더바 클릭으로 검색 모달 열림."
```

---

### Phase 3 완료 검증

- [ ] **Step 1: 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
npm test 2>&1 | tail -5
```

Expected: 0 errors, 빌드 OK, 4 tests pass.

- [ ] **Step 2: 커밋 로그**

```bash
cd /Users/loki/GenSub
git log --oneline feature/search ^master | cat
```

Expected: 8 커밋 (Phase 1 의 2 + Phase 2 의 3 + Phase 3 의 3).

Phase 3 완료. Phase 4 (영상 내 ⌘F) 진행.
