<script lang="ts">
  import { Plus, ChevronLeft } from 'lucide-svelte';

  import { api } from '$lib/api/jobs';
  import { current, reset } from '$lib/stores/current';
  import {
    history,
    pushHistory,
    removeFromHistory,
    type HistoryItem
  } from '$lib/stores/history';

  export let collapsed = false;
  export let onToggle: () => void = () => {};

  let editingId: string | null = null;
  let editValue = '';
  let validating = false;
  let validated = false;

  $: if (!collapsed) {
    validateOnce();
  }

  async function validateOnce() {
    if (validated || validating) return;
    validating = true;
    validated = true;
    const items: HistoryItem[] = [];
    const unsub = history.subscribe((h) => {
      items.push(...h);
    });
    unsub();
    for (const item of items) {
      try {
        const job = await api.getJob(item.jobId);
        if (job.title && job.title !== item.title) {
          pushHistory({ jobId: item.jobId, title: job.title, createdAt: item.createdAt });
        }
      } catch {
        removeFromHistory(item.jobId);
      }
    }
    validating = false;
  }

  function openJob(jobId: string) {
    current.set({
      screen: 'ready',
      jobId,
      job: null,
      progress: 1,
      stageMessage: '',
      errorMessage: null
    });
  }

  function startEdit(item: HistoryItem) {
    editingId = item.jobId;
    editValue = item.title ?? item.jobId;
  }

  function saveEdit(item: HistoryItem) {
    if (editValue.trim()) {
      pushHistory({ ...item, title: editValue.trim() });
    }
    editingId = null;
  }

  function cancelEdit() {
    editingId = null;
  }

  function handleEditKey(e: KeyboardEvent, item: HistoryItem) {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdit(item);
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  }

  // 날짜별 그룹핑
  function groupByDate(items: HistoryItem[]): { label: string; items: HistoryItem[] }[] {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);

    const groups: Map<string, HistoryItem[]> = new Map();
    for (const item of items) {
      const d = new Date(item.createdAt);
      const itemDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      let label: string;
      if (itemDate >= today) label = '오늘';
      else if (itemDate >= yesterday) label = '어제';
      else if (itemDate >= weekAgo) label = '이번 주';
      else label = `${d.getFullYear()}년 ${d.getMonth() + 1}월`;
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label)!.push(item);
    }
    return [...groups.entries()].map(([label, items]) => ({ label, items }));
  }

  $: activeJobId = $current.jobId;
  $: groups = groupByDate($history);
</script>

<aside
  class="fixed top-0 left-0 bottom-0 z-20 flex flex-col
         bg-bg-light dark:bg-bg-dark
         transition-all duration-300 ease-spring
         {collapsed ? 'w-0 overflow-hidden' : 'w-72'}
         shadow-[1px_0_0_0] shadow-divider-light dark:shadow-divider-dark"
>
  <!-- 헤더 -->
  <div class="flex items-center justify-between px-5 py-4 shrink-0">
    <button
      type="button"
      on:click={reset}
      class="text-body font-bold tracking-tight hover:opacity-60 transition-opacity"
      aria-label="홈으로"
    >GenSub</button>
    <div class="flex items-center gap-1">
      <button
        type="button"
        on:click={reset}
        class="p-2 rounded-xl hover:bg-divider-light dark:hover:bg-surface-dark-elevated
               text-text-secondary-light dark:text-text-secondary-dark transition-colors"
        aria-label="새 작업"
      >
        <Plus size={18} strokeWidth={2.5} />
      </button>
      <button
        type="button"
        on:click={onToggle}
        class="p-2 rounded-xl hover:bg-divider-light dark:hover:bg-surface-dark-elevated
               text-text-secondary-light dark:text-text-secondary-dark transition-colors"
        aria-label="사이드바 접기"
      >
        <ChevronLeft size={18} strokeWidth={2.5} />
      </button>
    </div>
  </div>

  <!-- 작업 리스트 -->
  <nav class="flex-1 overflow-y-auto px-3 pb-4" aria-label="작업 이력">
    {#if validating && $history.length === 0}
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark px-2 py-8 text-center">
        불러오는 중...
      </div>
    {:else if $history.length === 0}
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark px-2 py-8 text-center">
        아직 작업 이력이 없어요
      </div>
    {:else}
      {#each groups as group}
        <div class="mt-4 first:mt-1">
          <div class="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider
                      text-text-secondary-light dark:text-text-secondary-dark">
            {group.label}
          </div>
          {#each group.items as item (item.jobId)}
            <div
              class="group relative flex items-center rounded-xl my-0.5 transition-all duration-150
                     {activeJobId === item.jobId
                       ? 'bg-surface-light dark:bg-surface-dark shadow-sm'
                       : 'hover:bg-surface-light dark:hover:bg-surface-dark'}"
            >
              {#if editingId === item.jobId}
                <!-- svelte-ignore a11y-autofocus -->
                <input
                  type="text"
                  bind:value={editValue}
                  on:blur={() => saveEdit(item)}
                  on:keydown={(e) => handleEditKey(e, item)}
                  autofocus
                  class="flex-1 bg-transparent outline-none text-[14px] leading-snug
                         px-3 py-2.5 rounded-xl ring-2 ring-brand"
                />
              {:else}
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <div
                  class="flex-1 min-w-0 px-3 py-2.5 cursor-pointer"
                  on:click={() => openJob(item.jobId)}
                  on:dblclick|stopPropagation={() => startEdit(item)}
                >
                  <div class="truncate text-[14px] leading-snug
                              {activeJobId === item.jobId
                                ? 'font-semibold text-text-primary-light dark:text-text-primary-dark'
                                : 'text-text-primary-light dark:text-text-primary-dark'}">
                    {item.title ?? item.jobId}
                  </div>
                </div>
                <!-- 삭제: 호버 시 우측에 페이드인 -->
                <button
                  type="button"
                  class="absolute right-1.5 top-1/2 -translate-y-1/2
                         opacity-0 group-hover:opacity-100
                         p-1.5 rounded-lg
                         text-text-secondary-light dark:text-text-secondary-dark
                         hover:text-danger hover:bg-danger/10
                         transition-all duration-150"
                  on:click|stopPropagation={() => removeFromHistory(item.jobId)}
                  aria-label="삭제"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              {/if}
            </div>
          {/each}
        </div>
      {/each}
    {/if}
  </nav>
</aside>
