<script lang="ts">
  import { tick } from 'svelte';

  import { api } from '$lib/api/jobs';
  import type { SegmentDto } from '$lib/api/types';
  import EditableSegment from './EditableSegment.svelte';

  export let jobId: string;
  export let segments: SegmentDto[] = [];
  export let currentTime = 0;
  export let onJump: (t: number) => void = () => {};

  let activeIdx = -1;
  let editingIdx: number | null = null;
  let containerEl: HTMLDivElement;

  $: {
    const i = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);
    if (i !== activeIdx) {
      activeIdx = i;
      tick().then(() => {
        const el = containerEl?.querySelector(`[data-idx="${i}"]`) as HTMLElement | null;
        el?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      });
    }
  }

  function isLowConfidence(seg: SegmentDto): boolean {
    if (seg.avg_logprob == null) return false;
    return seg.avg_logprob < -1.0;
  }
</script>

<div bind:this={containerEl} class="space-y-2">
  {#each segments as seg, i (seg.idx)}
    <div
      data-idx={i}
      class="w-full text-left p-3 rounded-input transition-all
             {activeIdx === i
               ? 'bg-brand/10 border-l-4 border-brand scale-[1.02]'
               : 'hover:bg-divider-light dark:hover:bg-surface-dark-elevated'}
             {isLowConfidence(seg) ? 'bg-warning/10' : ''}"
    >
      <button
        type="button"
        on:click={() => onJump(seg.start)}
        class="w-full text-left text-caption mb-1 flex items-center justify-between
               text-text-secondary-light dark:text-text-secondary-dark
               hover:text-brand dark:hover:text-brand-dark transition-colors group"
      >
        <span class="flex items-center gap-1.5">
          <span class="opacity-50 group-hover:opacity-100 transition-opacity">▶</span>
          <span>{seg.start.toFixed(2)} → {seg.end.toFixed(2)}</span>
        </span>
        {#if seg.edited}
          <span class="text-brand">편집됨</span>
        {/if}
      </button>
      {#if editingIdx === i}
        <EditableSegment
          value={seg.text}
          editing={true}
          on:save={async (e) => {
            editingIdx = null;
            try {
              await api.patchSegment(jobId, seg.idx, { text: e.detail });
              segments[i] = { ...seg, text: e.detail, edited: true };
            } catch {}
          }}
          on:cancel={() => (editingIdx = null)}
        />
      {:else}
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span
          class="text-body cursor-text block"
          on:dblclick|stopPropagation={() => (editingIdx = i)}
        >{seg.text}</span>
      {/if}
      {#if activeIdx === i}
        <div class="flex gap-2 mt-2 text-caption flex-wrap">
          <button type="button" class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
            on:click={async () => {
              const next = Math.max(0, seg.start - 0.1);
              await api.patchSegment(jobId, seg.idx, { start: next });
              segments[i] = { ...seg, start: next };
            }}>시작 −0.1</button>
          <button type="button" class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
            on:click={async () => {
              const next = seg.start + 0.1;
              await api.patchSegment(jobId, seg.idx, { start: next });
              segments[i] = { ...seg, start: next };
            }}>시작 +0.1</button>
          <button type="button" class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
            on:click={async () => {
              const next = Math.max(seg.start + 0.1, seg.end - 0.1);
              await api.patchSegment(jobId, seg.idx, { end: next });
              segments[i] = { ...seg, end: next };
            }}>끝 −0.1</button>
          <button type="button" class="px-2 py-1 rounded bg-divider-light dark:bg-surface-dark-elevated"
            on:click={async () => {
              const next = seg.end + 0.1;
              await api.patchSegment(jobId, seg.idx, { end: next });
              segments[i] = { ...seg, end: next };
            }}>끝 +0.1</button>
          <button type="button" class="ml-auto px-2 py-1 rounded bg-brand text-white"
            on:click={async () => {
              try {
                await api.regenerateSegment(jobId, seg.idx);
                segments = await api.segments(jobId);
              } catch {}
            }}>↻ 재전사</button>
          <button type="button" class="px-2 py-1 rounded bg-success text-white"
            on:click={async () => {
              try {
                await api.exportClip(jobId, seg.start, seg.end);
              } catch {}
            }}>📎 구간 다운로드</button>
        </div>
      {/if}
    </div>
  {/each}
</div>
