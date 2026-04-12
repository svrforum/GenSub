<script lang="ts">
  import BurnDoneScreen from '$lib/screens/BurnDoneScreen.svelte';
  import ErrorScreen from '$lib/screens/ErrorScreen.svelte';
  import IdleScreen from '$lib/screens/IdleScreen.svelte';
  import ProcessingScreen from '$lib/screens/ProcessingScreen.svelte';
  import ReadyScreen from '$lib/screens/ReadyScreen.svelte';
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
  <ReadyScreen {jobId} />
{:else if $current.screen === 'burn_done' && jobId}
  <BurnDoneScreen {jobId} />
{:else if $current.screen === 'error'}
  <ErrorScreen />
{/if}
