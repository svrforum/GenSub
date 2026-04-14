<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { Moon, Sun, Menu } from 'lucide-svelte';
  import { initTheme, theme, toggleTheme } from '$lib/theme';
  import { initHistory } from '$lib/stores/history';
  import Sidebar from '$lib/ui/Sidebar.svelte';

  let sidebarCollapsed = false;

  onMount(() => {
    initTheme();
    initHistory();
    // 모바일에서는 기본으로 접기
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      sidebarCollapsed = true;
    }
  });
</script>

<Sidebar collapsed={sidebarCollapsed} onToggle={() => (sidebarCollapsed = !sidebarCollapsed)} />

<!-- Top bar: hamburger when collapsed + theme toggle -->
<header
  class="fixed top-0 z-10 flex items-center justify-between px-4 py-3 transition-all duration-300
         {sidebarCollapsed ? 'left-0' : 'left-72'} right-0"
>
  <div class="flex items-center gap-2">
    {#if sidebarCollapsed}
      <button
        type="button"
        on:click={() => (sidebarCollapsed = false)}
        class="p-2 rounded-lg hover:bg-divider-light dark:hover:bg-surface-dark-elevated"
        aria-label="사이드바 열기"
      >
        <Menu size={20} />
      </button>
      <span class="text-title tracking-tight font-bold">GenSub</span>
    {/if}
  </div>
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
</header>

<main
  class="pt-14 transition-all duration-300
         {sidebarCollapsed ? 'ml-0' : 'ml-72'}"
>
  <slot />
</main>
