<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { initTheme } from '$lib/theme';
  import { initHistory } from '$lib/stores/history';

  onMount(() => {
    initTheme();
    initHistory();
  });
</script>

<slot />
