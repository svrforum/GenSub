<script lang="ts">
  import BurnDoneScreen from '$lib/screens/BurnDoneScreen.svelte';
  import ErrorScreen from '$lib/screens/ErrorScreen.svelte';
  import IdleScreen from '$lib/screens/IdleScreen.svelte';
  import ProcessingScreen from '$lib/screens/ProcessingScreen.svelte';
  import ReadyScreen from '$lib/screens/ReadyScreen.svelte';
  import { current } from '$lib/stores/current';
</script>

{#if $current.screen === 'idle'}
  <IdleScreen />
{:else if $current.screen === 'processing' && $current.jobId}
  <ProcessingScreen jobId={$current.jobId} />
{:else if $current.screen === 'ready' && $current.jobId}
  <ReadyScreen jobId={$current.jobId} />
{:else if $current.screen === 'burn_done' && $current.jobId}
  <BurnDoneScreen jobId={$current.jobId} />
{:else if $current.screen === 'error'}
  <ErrorScreen />
{/if}
