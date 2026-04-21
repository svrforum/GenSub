<script lang="ts">
  import { Trash2 } from 'lucide-svelte';

  import type { MemoListItemDto } from '$lib/api/types';

  export let memo: MemoListItemDto;
  export let onOpen: (memo: MemoListItemDto) => void;
  export let onDelete: (memoId: number) => void;

  let hovered = false;

  function fmtMMSS(sec: number): string {
    const total = Math.floor(sec);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function handleClick() {
    if (!memo.job_alive) return;
    onOpen(memo);
  }

  function handleDelete(e: MouseEvent) {
    e.stopPropagation();
    if (confirm('이 메모를 삭제할까요?')) {
      onDelete(memo.id);
    }
  }
</script>

<li
  class="relative rounded-lg px-3 py-2 transition-colors
         {memo.job_alive
           ? 'hover:bg-black/[0.04] dark:hover:bg-white/[0.04] cursor-pointer'
           : 'opacity-50 cursor-not-allowed'}"
  on:mouseenter={() => (hovered = true)}
  on:mouseleave={() => (hovered = false)}
  on:click={handleClick}
  on:keydown={(e) => (e.key === 'Enter' ? handleClick() : null)}
  role="button"
  tabindex={memo.job_alive ? 0 : -1}
>
  <div class="text-[12px] leading-snug text-text-primary-light dark:text-text-primary-dark line-clamp-2">
    {memo.segment_text}
  </div>

  {#if memo.memo_text}
    <div class="mt-1 text-[11px] leading-snug
                text-text-secondary-light dark:text-text-secondary-dark
                line-clamp-2">
      💭 {memo.memo_text}
    </div>
  {/if}

  <div class="mt-1.5 text-[10px] text-text-secondary-light dark:text-text-secondary-dark
              flex items-center gap-1.5">
    <span class="truncate">{memo.job_title ?? '(제목 없음)'}</span>
    <span>·</span>
    <span class="tabular-nums shrink-0">{fmtMMSS(memo.start)}</span>
    {#if !memo.job_alive}
      <span class="ml-auto px-1.5 py-0.5 rounded bg-text-secondary-light/10 text-[9px]">
        영상 삭제됨
      </span>
    {/if}
  </div>

  {#if hovered}
    <button
      type="button"
      on:click={handleDelete}
      class="absolute right-2 top-2 p-1 rounded
             text-text-secondary-light dark:text-text-secondary-dark
             hover:bg-danger/10 hover:text-danger transition-colors"
      aria-label="메모 삭제"
    >
      <Trash2 size={13} />
    </button>
  {/if}
</li>
