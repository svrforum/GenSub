<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { initTheme } from '$lib/theme';
  import { initHistory } from '$lib/stores/history';
  import Header from '$lib/ui/Header.svelte';

  let recentOpen = false;

  onMount(() => {
    initTheme();
    initHistory();
  });
</script>

<Header onRecentClick={() => (recentOpen = !recentOpen)} />

<main class="pt-16">
  <slot />
</main>
