<script lang="ts">
  import IdleScreen from '$lib/screens/IdleScreen.svelte';
  import ProcessingScreen from '$lib/screens/ProcessingScreen.svelte';
  import { current } from '$lib/stores/current';

  function getJobId(): string | undefined {
    if (typeof window === 'undefined') return undefined;
    return (window as unknown as { __gensubCurrentJobId?: string }).__gensubCurrentJobId;
  }

  $: jobId = getJobId();
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
