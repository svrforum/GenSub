<script lang="ts">
  import { tick } from 'svelte';

  import type { SegmentDto } from '$lib/api/types';

  export let segments: SegmentDto[] = [];
  export let currentTime = 0;
  export let onJump: (t: number) => void = () => {};

  let activeIdx = -1;
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
    <button
      type="button"
      data-idx={i}
      on:click={() => onJump(seg.start)}
      class="w-full text-left p-3 rounded-input transition-all
             {activeIdx === i
               ? 'bg-brand/10 border-l-4 border-brand scale-[1.02]'
               : 'hover:bg-divider-light dark:hover:bg-surface-dark-elevated'}
             {isLowConfidence(seg) ? 'bg-warning/10' : ''}"
    >
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mb-1 flex justify-between">
        <span>{seg.start.toFixed(2)} → {seg.end.toFixed(2)}</span>
        {#if seg.edited}
          <span class="text-brand">편집됨</span>
        {/if}
      </div>
      <div class="text-body">{seg.text}</div>
    </button>
  {/each}
</div>
