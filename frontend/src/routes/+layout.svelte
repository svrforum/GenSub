<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { Menu, Moon, Sun } from 'lucide-svelte';
  import { initTheme, theme, toggleTheme } from '$lib/theme';
  import { initHistory } from '$lib/stores/history';
  import { current } from '$lib/stores/current';
  import { searchOpen } from '$lib/stores/search';
  import Sidebar from '$lib/ui/Sidebar.svelte';
  import SearchBar from '$lib/ui/SearchBar.svelte';
  import SearchModal from '$lib/ui/SearchModal.svelte';

  $: isProcessing = $current.screen === 'processing';

  let sidebarCollapsed = false;

  function handleGlobalKey(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchOpen.set(true);
    }
  }

  onMount(() => {
    initTheme();
    initHistory();
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      sidebarCollapsed = true;
    }
    window.addEventListener('keydown', handleGlobalKey);
    return () => window.removeEventListener('keydown', handleGlobalKey);
  });
</script>

<Sidebar collapsed={sidebarCollapsed} onToggle={() => (sidebarCollapsed = !sidebarCollapsed)} />

<!-- 처리 중일 때 사이드바/헤더 클릭 차단 -->
{#if isProcessing && !sidebarCollapsed}
  <div class="fixed top-0 left-0 w-[260px] bottom-0 z-30 bg-black/5 dark:bg-white/5 cursor-not-allowed" />
{/if}

<header
  class="fixed top-0 z-10 flex items-center gap-3 px-5 h-14 transition-all duration-300 ease-spring
         {sidebarCollapsed ? 'left-0' : 'left-[260px]'} right-0"
>
  <div class="flex items-center gap-2 shrink-0">
    {#if sidebarCollapsed}
      <button
        type="button"
        on:click={() => (sidebarCollapsed = false)}
        class="p-2 rounded-xl hover:bg-divider-light dark:hover:bg-surface-dark-elevated
               text-text-secondary-light dark:text-text-secondary-dark transition-colors"
        aria-label="사이드바 열기"
      >
        <Menu size={20} />
      </button>
      <span class="text-body font-bold tracking-tight">GenSub</span>
    {/if}
  </div>

  <!-- SearchBar 가운데 영역 -->
  <div class="flex-1 flex justify-center">
    <SearchBar />
  </div>

  <button
    type="button"
    on:click={toggleTheme}
    class="p-2 rounded-xl hover:bg-divider-light dark:hover:bg-surface-dark-elevated
           text-text-secondary-light dark:text-text-secondary-dark transition-colors shrink-0"
    aria-label="다크 모드 전환"
  >
    {#if $theme === 'dark'}
      <Sun size={18} />
    {:else}
      <Moon size={18} />
    {/if}
  </button>
</header>

<main
  class="pt-14 min-h-screen transition-all duration-300 ease-spring
         {sidebarCollapsed ? 'ml-0' : 'ml-[260px]'}"
>
  <slot />
</main>

<SearchModal />
