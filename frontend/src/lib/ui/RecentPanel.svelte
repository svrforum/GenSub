<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';

  import { api } from '$lib/api/jobs';
  import { current } from '$lib/stores/current';
  import {
    history,
    pushHistory,
    removeFromHistory,
    type HistoryItem
  } from '$lib/stores/history';

  export let open = false;
  export let onClose: () => void = () => {};

  let validating = false;

  // 패널이 열릴 때 각 항목을 백엔드에서 검증 + 제목 갱신
  $: if (open) {
    validateHistory();
  }

  async function validateHistory() {
    validating = true;
    const items: HistoryItem[] = [];
    history.subscribe((h) => {
      items.push(...h);
    })();

    for (const item of items) {
      try {
        const job = await api.getJob(item.jobId);
        // 제목이 없거나 ID로 표시되던 항목 → 실제 제목으로 갱신
        if (job.title && job.title !== item.title) {
          pushHistory({ jobId: item.jobId, title: job.title, createdAt: item.createdAt });
        }
      } catch {
        // 404 등 → DB에서 삭제된 작업이므로 히스토리에서 제거
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
    onClose();
  }
</script>

{#if open}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="fixed inset-0 z-40 bg-black/30" on:click={onClose} transition:fade={{ duration: 200 }} />
  <aside
    class="fixed top-0 right-0 bottom-0 z-50 w-[360px] bg-surface-light dark:bg-surface-dark
           shadow-card p-6 overflow-y-auto"
    transition:fly={{ x: 400, duration: 380, easing: cubicOut }}
  >
    <div class="text-title mb-6">최근 작업</div>
    {#if validating && $history.length > 0}
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mb-4">
        확인 중...
      </div>
    {/if}
    {#if $history.length === 0 && !validating}
      <div class="text-body text-text-secondary-light dark:text-text-secondary-dark">
        아직 처리한 영상이 없어요
      </div>
    {:else}
      <div class="flex flex-col gap-3">
        {#each $history as item (item.jobId)}
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
