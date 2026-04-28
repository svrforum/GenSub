<script lang="ts">
  import { Search } from 'lucide-svelte';

  import { searchOpen, searchQuery } from '$lib/stores/search';

  function handleClick() {
    searchOpen.set(true);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      searchOpen.set(true);
    }
  }
</script>

<button
  type="button"
  on:click={handleClick}
  on:keydown={handleKey}
  class="flex items-center gap-2 w-full max-w-[360px]
         h-9 px-3 rounded-xl
         bg-black/[0.04] dark:bg-white/[0.06]
         hover:bg-black/[0.06] dark:hover:bg-white/[0.08]
         text-text-secondary-light dark:text-text-secondary-dark
         text-[13px] transition-colors text-left"
  aria-label="검색 열기"
>
  <Search size={15} strokeWidth={1.75} />
  <span class="flex-1 truncate">
    {#if $searchQuery}
      {$searchQuery}
    {:else}
      자막·메모·영상 검색…
    {/if}
  </span>
  <kbd class="hidden sm:inline-flex text-[10px] px-1.5 py-0.5 rounded
              border border-black/[0.08] dark:border-white/[0.1]
              text-text-secondary-light dark:text-text-secondary-dark">
    ⌘K
  </kbd>
</button>
