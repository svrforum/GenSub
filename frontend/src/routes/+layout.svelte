<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { initTheme } from '$lib/theme';
  import { initHistory } from '$lib/stores/history';
  import Header from '$lib/ui/Header.svelte';
  import RecentPanel from '$lib/ui/RecentPanel.svelte';

  let recentOpen = false;

  onMount(() => {
    initTheme();
    initHistory();
  });
</script>

<Header onRecentClick={() => (recentOpen = true)} />

<main class="pt-16">
  <slot />
</main>

<RecentPanel open={recentOpen} onClose={() => (recentOpen = false)} />
