<script lang="ts">
  import { tick } from 'svelte';

  import { api } from '$lib/api/jobs';
  import type { SegmentDto } from '$lib/api/types';
  import EditableSegment from './EditableSegment.svelte';

  export let jobId: string;
  export let segments: SegmentDto[] = [];
  export let currentTime = 0;
  export let onJump: (t: number) => void = () => {};
  export let language: string | null = null;

  let activeIdx = -1;
  let editingIdx: number | null = null;
  let containerEl: HTMLDivElement;
  let selectedIndices: Set<number> = new Set();
  let lastClickedIdx: number | null = null;

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

  function fmtTime(sec: number): string {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function isLowConfidence(seg: SegmentDto): boolean {
    if (seg.avg_logprob == null) return false;
    return seg.avg_logprob < -1.0;
  }

  function handleSegClick(i: number, e: MouseEvent) {
    if (e.ctrlKey || e.metaKey) {
      // Ctrl/Cmd + 클릭: 토글 선택
      selectedIndices = new Set(selectedIndices);
      if (selectedIndices.has(i)) selectedIndices.delete(i);
      else selectedIndices.add(i);
      lastClickedIdx = i;
    } else if (e.shiftKey && lastClickedIdx !== null) {
      // Shift + 클릭: 범위 선택
      const from = Math.min(lastClickedIdx, i);
      const to = Math.max(lastClickedIdx, i);
      selectedIndices = new Set(selectedIndices);
      for (let j = from; j <= to; j++) selectedIndices.add(j);
    } else {
      // 일반 클릭: 단일 선택 해제 후 점프
      selectedIndices = new Set();
      lastClickedIdx = i;
      onJump(segments[i].start);
    }
  }

  function clearSelection() {
    selectedIndices = new Set();
  }

  function translateSelected() {
    const texts = [...selectedIndices]
      .sort((a, b) => a - b)
      .map((i) => segments[i]?.text)
      .filter(Boolean)
      .join('\n');
    if (!texts) return;
    const sl = language || 'auto';
    const tl = sl === 'ko' ? 'en' : 'ko';
    window.open(
      `https://translate.google.com/?sl=${sl}&tl=${tl}&text=${encodeURIComponent(texts)}&op=translate`,
      '_blank'
    );
  }

  $: hasSelection = selectedIndices.size > 0;
</script>

<!-- 선택 액션 바 -->
{#if hasSelection}
  <div class="sticky top-0 z-10 flex items-center justify-between gap-2
              bg-brand/10 dark:bg-brand/20 backdrop-blur rounded-xl px-3 py-2 mb-2">
    <span class="text-caption font-medium text-brand">
      {selectedIndices.size}개 선택됨
    </span>
    <div class="flex items-center gap-1.5">
      <button
        type="button"
        class="text-caption px-2.5 py-1 rounded-lg bg-brand text-white
               hover:bg-brand-pressed transition-colors"
        on:click={translateSelected}
      >🌐 번역</button>
      <button
        type="button"
        class="text-caption px-2.5 py-1 rounded-lg
               text-text-secondary-light dark:text-text-secondary-dark
               hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
        on:click={clearSelection}
      >선택 해제</button>
    </div>
  </div>
{/if}

<div bind:this={containerEl} class="space-y-2">
  {#each segments as seg, i (seg.idx)}
    <div
      data-idx={i}
      class="group w-full text-left p-3 rounded-input transition-all
             {selectedIndices.has(i)
               ? 'bg-brand/10 ring-1 ring-brand/30'
               : activeIdx === i
                 ? 'bg-brand/10 border-l-4 border-brand scale-[1.02]'
                 : 'hover:bg-divider-light dark:hover:bg-surface-dark-elevated'}
             {isLowConfidence(seg) ? 'bg-warning/10' : ''}"
    >
      <button
        type="button"
        on:click={(e) => handleSegClick(i, e)}
        class="w-full text-left text-caption mb-1 flex items-center justify-between
               text-text-secondary-light dark:text-text-secondary-dark
               hover:text-brand dark:hover:text-brand-dark transition-colors group"
      >
        <span class="flex items-center gap-1.5">
          {#if selectedIndices.has(i)}
            <span class="text-brand">✓</span>
          {:else}
            <span class="opacity-50 group-hover:opacity-100 transition-opacity">▶</span>
          {/if}
          <span>{fmtTime(seg.start)} → {fmtTime(seg.end)}</span>
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
        <div class="flex items-start gap-1.5">
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <span
            class="text-body cursor-text block flex-1"
            on:dblclick|stopPropagation={() => (editingIdx = i)}
          >{seg.text}</span>
          <a
            href="https://translate.google.com/?sl=auto&tl=ko&text={encodeURIComponent(seg.text)}&op=translate"
            target="_blank"
            rel="noopener noreferrer"
            class="shrink-0 mt-0.5 opacity-0 group-hover:opacity-60 hover:!opacity-100
                   text-text-secondary-light dark:text-text-secondary-dark transition-opacity"
            title="이 구간 번역하기"
            on:click|stopPropagation
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m5 8 6 6M4 14l6-6 2-3M2 5h12M7 2h1M22 22l-5-10-5 10M14 18h6" />
            </svg>
          </a>
        </div>
      {/if}
      {#if activeIdx === i && !hasSelection}
        <div class="mt-2">
          <button type="button"
            class="text-caption px-2.5 py-1 rounded-lg
                   text-text-secondary-light dark:text-text-secondary-dark
                   hover:bg-divider-light dark:hover:bg-surface-dark-elevated transition-colors"
            on:click={async () => {
              try {
                await api.exportClip(jobId, seg.start, seg.end);
              } catch {}
            }}>📎 이 구간 다운로드</button>
        </div>
      {/if}
    </div>
  {/each}
</div>
