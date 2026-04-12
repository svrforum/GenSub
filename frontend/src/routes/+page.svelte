<script lang="ts">
  import IdleScreen from '$lib/screens/IdleScreen.svelte';
  import { current } from '$lib/stores/current';
</script>

{#if $current.screen === 'idle'}
  <IdleScreen />
{:else}
  <!-- Processing / Ready / Error screens from Phase 11+ -->
  <div class="min-h-screen flex items-center justify-center">
    <p class="text-body text-text-secondary-light dark:text-text-secondary-dark">
      화면: {$current.screen}
    </p>
  </div>
{/if}
