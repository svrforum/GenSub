<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Search, X, ChevronUp, ChevronDown } from 'lucide-svelte';

  import type { SegmentDto } from '$lib/api/types';

  /** 현재 영상의 모든 세그먼트. 이 배열로 클라이언트 매치 수행. */
  export let segments: SegmentDto[] = [];

  /** 매치된 세그먼트 클릭/Enter 시 호출. */
  export let onJump: (segment: SegmentDto) => void = () => {};

  /** 부모가 inputEl 에 포커스 / 오버레이 close 제어할 수 있게. */
  export let open = false;

  let inputEl: HTMLInputElement | null = null;
  let query = '';

  $: matches = computeMatches(segments, query);
  $: matchCount = matches.length;

  let currentIdx = 0;

  $: if (open && inputEl) {
    queueMicrotask(() => inputEl?.focus());
  }

  $: if (matches.length > 0 && currentIdx >= matches.length) {
    currentIdx = 0;
  }

  function computeMatches(segs: SegmentDto[], q: string): SegmentDto[] {
    const trimmed = q.trim().toLowerCase();
    if (!trimmed) return [];
    return segs.filter((s) => s.text.toLowerCase().includes(trimmed));
  }

  function gotoMatch(direction: 1 | -1) {
    if (matches.length === 0) return;
    currentIdx = (currentIdx + direction + matches.length) % matches.length;
    onJump(matches[currentIdx]);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) gotoMatch(-1);
      else gotoMatch(1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      gotoMatch(-1);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      gotoMatch(1);
    }
  }

  function close() {
    open = false;
    query = '';
    currentIdx = 0;
  }

  /** 부모에서 매치 정보를 받을 수 있도록 export. */
  export function getMatchedIdxSet(): Set<number> {
    return new Set(matches.map((m) => m.idx));
  }

  export function getCurrentMatchIdx(): number | null {
    return matches[currentIdx]?.idx ?? null;
  }

  onDestroy(() => {
    // nothing — open 은 부모가 관리
  });
</script>

{#if open}
  <div
    class="absolute top-2 right-2 z-20 flex items-center gap-2
           bg-white dark:bg-[#1c1c1e]
           border border-black/[0.08] dark:border-white/[0.1]
           rounded-xl shadow-lg
           px-2 py-1.5"
  >
    <Search size={14} strokeWidth={1.75}
            class="text-text-secondary-light dark:text-text-secondary-dark shrink-0" />
    <input
      bind:this={inputEl}
      bind:value={query}
      on:keydown={handleKey}
      type="text"
      placeholder="이 영상에서 검색…"
      class="w-48 bg-transparent border-0 outline-none text-[13px]
             text-text-primary-light dark:text-text-primary-dark
             placeholder:text-text-secondary-light dark:placeholder:text-text-secondary-dark"
    />
    <span class="shrink-0 text-[11px] text-text-secondary-light dark:text-text-secondary-dark tabular-nums">
      {#if query.trim() === ''}
        &nbsp;
      {:else if matchCount === 0}
        0
      {:else}
        {currentIdx + 1}/{matchCount}
      {/if}
    </span>
    <button
      type="button"
      on:click={() => gotoMatch(-1)}
      disabled={matchCount === 0}
      class="p-1 rounded hover:bg-black/[0.04] dark:hover:bg-white/[0.06]
             text-text-secondary-light dark:text-text-secondary-dark
             disabled:opacity-30 disabled:hover:bg-transparent"
      aria-label="이전 매치"
    >
      <ChevronUp size={14} strokeWidth={1.75} />
    </button>
    <button
      type="button"
      on:click={() => gotoMatch(1)}
      disabled={matchCount === 0}
      class="p-1 rounded hover:bg-black/[0.04] dark:hover:bg-white/[0.06]
             text-text-secondary-light dark:text-text-secondary-dark
             disabled:opacity-30 disabled:hover:bg-transparent"
      aria-label="다음 매치"
    >
      <ChevronDown size={14} strokeWidth={1.75} />
    </button>
    <button
      type="button"
      on:click={close}
      class="p-1 rounded hover:bg-black/[0.04] dark:hover:bg-white/[0.06]
             text-text-secondary-light dark:text-text-secondary-dark"
      aria-label="검색 닫기"
    >
      <X size={14} strokeWidth={1.75} />
    </button>
  </div>
{/if}
