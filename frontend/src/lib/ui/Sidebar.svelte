<script lang="ts">
  import { api } from '$lib/api/jobs';
  import { current, reset } from '$lib/stores/current';
  import { history, pushHistory, removeFromHistory, type HistoryItem } from '$lib/stores/history';

  export let collapsed = false;
  export let onToggle: () => void = () => {};

  let editingId: string | null = null;
  let editValue = '';
  let validating = false;
  let validated = false;

  // Validate history on first open
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

  $: activeJobId = $current.jobId;
</script>

<aside
  class="fixed top-0 left-0 bottom-0 z-20 flex flex-col
         bg-surface-light dark:bg-surface-dark border-r border-divider-light dark:border-divider-dark
         transition-all duration-300
         {collapsed ? 'w-0 overflow-hidden' : 'w-72'}"
>
  <div class="flex items-center justify-between p-4 border-b border-divider-light dark:border-divider-dark shrink-0">
    <button
      type="button"
      on:click={reset}
      class="text-title tracking-tight font-bold hover:opacity-70 transition-opacity"
      aria-label="홈으로"
    >GenSub</button>
    <button
      type="button"
      on:click={onToggle}
      class="p-1.5 rounded-lg hover:bg-divider-light dark:hover:bg-surface-dark-elevated"
      aria-label="사이드바 접기"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 18l-6-6 6-6" />
      </svg>
    </button>
  </div>

  <div class="flex-1 overflow-y-auto p-2">
    {#if validating && $history.length === 0}
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark p-3">
        확인 중...
      </div>
    {:else if $history.length === 0}
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark p-3">
        작업 이력이 없어요
      </div>
    {:else}
      {#each $history as item (item.jobId)}
        <div
          class="group flex items-center gap-1 rounded-lg px-3 py-2.5 cursor-pointer transition-colors
                 {activeJobId === item.jobId
                   ? 'bg-brand/10 text-brand'
                   : 'hover:bg-divider-light dark:hover:bg-surface-dark-elevated'}"
        >
          {#if editingId === item.jobId}
            <!-- svelte-ignore a11y-autofocus -->
            <input
              type="text"
              bind:value={editValue}
              on:blur={() => saveEdit(item)}
              on:keydown={(e) => handleEditKey(e, item)}
              autofocus
              class="flex-1 bg-transparent text-body outline-none border-b border-brand px-0 text-sm"
            />
          {:else}
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
              class="flex-1 min-w-0"
              on:click={() => openJob(item.jobId)}
              on:dblclick|stopPropagation={() => startEdit(item)}
            >
              <div class="text-body truncate text-sm">{item.title ?? item.jobId}</div>
              <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark text-xs">
                {new Date(item.createdAt).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
              </div>
            </div>
          {/if}
          <button
            type="button"
            class="opacity-0 group-hover:opacity-100 text-caption text-danger shrink-0 transition-opacity"
            on:click|stopPropagation={() => removeFromHistory(item.jobId)}
            aria-label="삭제"
          >×</button>
        </div>
      {/each}
    {/if}
  </div>
</aside>
