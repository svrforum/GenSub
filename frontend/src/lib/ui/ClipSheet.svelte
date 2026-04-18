<script lang="ts">
  import { api } from '$lib/api/jobs';
  import BottomSheet from '$lib/ui/BottomSheet.svelte';
  import Button from '$lib/ui/Button.svelte';
  import Segmented from '$lib/ui/Segmented.svelte';

  export let open = false;
  export let jobId: string;
  export let durationSec: number;
  export let currentTime = 0;
  export let onClose: () => void = () => {};

  let startMin = 0;
  let startSec = 0;
  let endMin = 0;
  let endSec = 0;
  let burnSubs = true;
  let size: string = '42';
  let outline = true;
  let busy = false;
  let errorText: string | null = null;

  const sizeOptions = [
    { value: '32', label: '작게' },
    { value: '42', label: '중간' },
    { value: '54', label: '크게' }
  ];

  $: if (open) {
    const s = Math.floor(currentTime);
    startMin = Math.floor(s / 60);
    startSec = s % 60;
    const e = Math.min(Math.floor(currentTime + 30), Math.floor(durationSec));
    endMin = Math.floor(e / 60);
    endSec = e % 60;
    errorText = null;
  }

  $: startTotal = startMin * 60 + startSec;
  $: endTotal = endMin * 60 + endSec;
  $: rangeValid = endTotal > startTotal && startTotal >= 0 && endTotal <= durationSec;
  $: rangeDuration = Math.max(0, endTotal - startTotal);

  function fmt(sec: number): string {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  async function download() {
    if (!rangeValid || busy) return;
    busy = true;
    errorText = null;
    try {
      await api.exportClip(jobId, startTotal, endTotal, burnSubs, {
        size: parseInt(size, 10),
        outline
      });
    } catch (e) {
      errorText = e instanceof Error ? e.message : '다운로드 실패';
    } finally {
      busy = false;
    }
  }
</script>

<BottomSheet {open} {onClose}>
  <div class="flex flex-col gap-5 py-2">
    <div>
      <div class="text-title">구간 선택 다운로드</div>
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mt-1">
        원하는 구간만 잘라서 다운로드해요
      </div>
    </div>

    <!-- 시간 선택 -->
    <div class="flex items-center gap-4">
      <div class="flex-1">
        <label class="text-caption text-text-secondary-light dark:text-text-secondary-dark mb-1 block">시작</label>
        <div class="flex items-center gap-1">
          <input type="number" min="0" max={Math.floor(durationSec / 60)} bind:value={startMin}
            class="w-16 px-2 py-2 bg-divider-light dark:bg-surface-dark-elevated rounded-input text-body text-center" />
          <span class="text-body">분</span>
          <input type="number" min="0" max="59" bind:value={startSec}
            class="w-16 px-2 py-2 bg-divider-light dark:bg-surface-dark-elevated rounded-input text-body text-center" />
          <span class="text-body">초</span>
        </div>
      </div>
      <span class="text-title mt-5">→</span>
      <div class="flex-1">
        <label class="text-caption text-text-secondary-light dark:text-text-secondary-dark mb-1 block">끝</label>
        <div class="flex items-center gap-1">
          <input type="number" min="0" max={Math.floor(durationSec / 60)} bind:value={endMin}
            class="w-16 px-2 py-2 bg-divider-light dark:bg-surface-dark-elevated rounded-input text-body text-center" />
          <span class="text-body">분</span>
          <input type="number" min="0" max="59" bind:value={endSec}
            class="w-16 px-2 py-2 bg-divider-light dark:bg-surface-dark-elevated rounded-input text-body text-center" />
          <span class="text-body">초</span>
        </div>
      </div>
    </div>

    <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
      {#if rangeValid}
        {fmt(startTotal)} ~ {fmt(endTotal)} ({rangeDuration}초)
      {:else}
        <span class="text-danger">유효하지 않은 구간이에요</span>
      {/if}
    </div>

    <!-- 자막 옵션 -->
    {#if burnSubs}
      <div class="flex items-center justify-between">
        <span class="text-body">자막 크기</span>
        <Segmented options={sizeOptions} bind:value={size} />
      </div>

      <label class="flex items-center justify-between text-body">
        <span>외곽선</span>
        <input type="checkbox" bind:checked={outline} class="w-12 h-7 rounded-full" />
      </label>
    {/if}

    <label class="flex items-center justify-between text-body">
      <span>자막 포함</span>
      <input type="checkbox" bind:checked={burnSubs} class="w-12 h-7 rounded-full" />
    </label>

    {#if errorText}
      <div class="text-caption text-danger">{errorText}</div>
    {/if}

    <Button variant="primary" fullWidth disabled={!rangeValid || busy} on:click={download}>
      {busy ? '다운로드 중...' : '다운로드'}
    </Button>
    <Button variant="ghost" fullWidth on:click={onClose}>취소</Button>
  </div>
</BottomSheet>
