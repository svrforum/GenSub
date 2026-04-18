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
