<script lang="ts">
  import { History, Moon, Sun } from 'lucide-svelte';

  import { theme, toggleTheme } from '$lib/theme';

  export let onRecentClick: () => void = () => {};
</script>

<header class="fixed top-0 inset-x-0 z-30 flex items-center justify-between px-6 py-4 backdrop-blur">
  <div class="text-title tracking-tight">GenSub</div>
  <div class="flex items-center gap-2">
    <button
      type="button"
      on:click={onRecentClick}
      class="p-2 rounded-full hover:bg-divider-light dark:hover:bg-surface-dark-elevated"
      aria-label="최근 작업"
    >
      <History size={20} />
    </button>
    <button
      type="button"
      on:click={toggleTheme}
      class="p-2 rounded-full hover:bg-divider-light dark:hover:bg-surface-dark-elevated"
      aria-label="다크 모드 전환"
    >
      {#if $theme === 'dark'}
        <Sun size={20} />
      {:else}
        <Moon size={20} />
      {/if}
    </button>
  </div>
</header>
