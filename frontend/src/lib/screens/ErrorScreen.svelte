<script lang="ts">
  import { current, reset } from '$lib/stores/current';
  import Button from '$lib/ui/Button.svelte';

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
