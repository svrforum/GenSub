<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Search, FileVideo, Bookmark, MessageSquare, Loader2 } from 'lucide-svelte';

  import type { SearchHit } from '$lib/api/types';
  import { openMemo } from '$lib/stores/current';
  import {
    closeSearch,
    scheduleSearch,
    searchLoading,
    searchOpen,
    searchQuery,
    searchResults,
  } from '$lib/stores/search';

  let inputEl: HTMLInputElement | null = null;

  // open 될 때 자동 포커스
  $: if ($searchOpen && inputEl) {
    queueMicrotask(() => inputEl?.focus());
  }

  // query 변경 시 debounce 검색
  $: scheduleSearch($searchQuery);

  function handleBackdrop() {
    closeSearch();
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      closeSearch();
    }
  }

  function handleResultClick(hit: SearchHit) {
    openMemo(hit.job_id, hit.start ?? 0);
    closeSearch();
  }

  function fmtMMSS(sec: number | undefined): string {
    if (sec === undefined) return '';
    const total = Math.floor(sec);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function previewText(hit: SearchHit): string {
    if (hit.kind === 'memo') return hit.memo_text || hit.segment_text || '';
    if (hit.kind === 'segment') return hit.segment_text || '';
    return hit.job_title || '';
  }

  onDestroy(() => {
    // store는 보존, listener만 정리
  });
</script>

{#if $searchOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
    on:click={handleBackdrop}
    on:keydown={handleKey}
  >
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      class="fixed left-1/2 top-16 -translate-x-1/2 w-[min(640px,calc(100vw-32px))]
             max-h-[min(500px,calc(100vh-128px))]
             bg-white dark:bg-[#1c1c1e]
             rounded-2xl shadow-2xl border border-black/[0.06] dark:border-white/[0.06]
             flex flex-col overflow-hidden"
      on:click|stopPropagation
    >
      <!-- 입력창 -->
      <div class="flex items-center gap-3 px-4 h-14 border-b border-black/[0.06] dark:border-white/[0.06]">
        <span class="text-text-secondary-light dark:text-text-secondary-dark shrink-0 inline-flex">
          <Search size={18} strokeWidth={1.75} />
        </span>
        <input
          bind:this={inputEl}
          bind:value={$searchQuery}
          on:keydown={handleKey}
          type="text"
          placeholder="자막·메모·영상 검색…"
          class="flex-1 bg-transparent border-0 outline-none
                 text-body text-text-primary-light dark:text-text-primary-dark
                 placeholder:text-text-secondary-light dark:placeholder:text-text-secondary-dark"
        />
        {#if $searchLoading}
          <span class="text-text-secondary-light dark:text-text-secondary-dark inline-flex animate-spin">
            <Loader2 size={16} />
          </span>
        {/if}
        <button
          type="button"
          on:click={closeSearch}
          class="text-[11px] px-1.5 py-0.5 rounded
                 border border-black/[0.08] dark:border-white/[0.1]
                 text-text-secondary-light dark:text-text-secondary-dark
                 hover:bg-black/[0.04] dark:hover:bg-white/[0.06]"
        >
          Esc
        </button>
      </div>

      <!-- 결과 -->
      <div class="flex-1 overflow-y-auto">
        {#if $searchQuery.trim() === ''}
          <div class="px-6 py-12 text-center text-[13px]
                      text-text-secondary-light dark:text-text-secondary-dark">
            검색어를 입력하세요.
            <br />
            영상 제목 · 메모 · 자막 모두 검색합니다.
          </div>
        {:else if $searchResults.length === 0 && !$searchLoading}
          <div class="px-6 py-12 text-center text-[13px]
                      text-text-secondary-light dark:text-text-secondary-dark">
            결과가 없어요.
          </div>
        {:else}
          <ul class="py-2">
            {#each $searchResults as hit (hit.kind + '-' + (hit.memo_id ?? hit.segment_idx ?? hit.job_id))}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
              <!-- svelte-ignore a11y-no-noninteractive-element-to-interactive-role -->
              <li
                role="button"
                tabindex="0"
                class="flex items-start gap-3 px-4 py-2.5
                       hover:bg-black/[0.04] dark:hover:bg-white/[0.04]
                       cursor-pointer transition-colors"
                on:click={() => handleResultClick(hit)}
                on:keydown={(e) => e.key === 'Enter' && handleResultClick(hit)}
              >
                <span class="shrink-0 pt-0.5
                             text-text-secondary-light dark:text-text-secondary-dark">
                  {#if hit.kind === 'job'}
                    <FileVideo size={14} strokeWidth={1.75} />
                  {:else if hit.kind === 'memo'}
                    <Bookmark size={14} strokeWidth={1.75} />
                  {:else}
                    <MessageSquare size={14} strokeWidth={1.75} />
                  {/if}
                </span>
                <div class="flex-1 min-w-0">
                  <div class="text-[13px] leading-snug
                              text-text-primary-light dark:text-text-primary-dark
                              line-clamp-2">
                    {previewText(hit)}
                  </div>
                  <div class="mt-0.5 text-[11px]
                              text-text-secondary-light dark:text-text-secondary-dark
                              flex items-center gap-1.5">
                    {#if hit.kind !== 'job'}
                      <span class="truncate">{hit.job_title ?? '(제목 없음)'}</span>
                      <span>·</span>
                      <span class="tabular-nums shrink-0">{fmtMMSS(hit.start)}</span>
                    {:else}
                      <span class="opacity-70">영상</span>
                    {/if}
                  </div>
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  </div>
{/if}
