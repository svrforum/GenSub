<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  import { api } from '$lib/api/jobs';
  import type { JobDto, SegmentDto } from '$lib/api/types';
  import DownloadBar from '$lib/ui/DownloadBar.svelte';
  import BurnSheet from '$lib/ui/BurnSheet.svelte';
  import ClipSheet from '$lib/ui/ClipSheet.svelte';
  import SegmentList from '$lib/ui/SegmentList.svelte';
  import VideoPlayer from '$lib/ui/VideoPlayer.svelte';
  import { installShortcuts } from './useShortcuts';
  import { reset } from '$lib/stores/current';

  export let jobId: string;

  let job: JobDto | null = null;
  let segments: SegmentDto[] = [];
  let loading = true;
  let errorText: string | null = null;
  let playerRef: VideoPlayer | null = null;
  let currentTime = 0;
  let showBurnSheet = false;
  let showClipSheet = false;
  let unshort: (() => void) | null = null;
  let videoError = false;

  onMount(async () => {
    try {
      [job, segments] = await Promise.all([api.getJob(jobId), api.segments(jobId)]);
    } catch (e) {
      errorText = e instanceof Error ? e.message : '불러올 수 없어요';
    } finally {
      loading = false;
    }
  });

  onMount(() => {
    unshort = installShortcuts({
      togglePlay: () => playerRef?.togglePlay(),
      prevSegment: () => {
        const i = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);
        if (i > 0) playerRef?.seekTo(segments[i - 1].start);
      },
      nextSegment: () => {
        const i = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);
        if (i >= 0 && i < segments.length - 1) playerRef?.seekTo(segments[i + 1].start);
      },
      seekRelative: (d) => {
        const t = Math.max(0, currentTime + d);
        playerRef?.seekTo(t);
      },
      toggleSearch: () => {}
    });
  });

  onDestroy(() => {
    unshort?.();
  });

  function handleBurnClick() {
    showBurnSheet = true;
  }
</script>

<div class="min-h-screen px-6 py-8 max-w-7xl mx-auto">
  {#if loading}
    <div class="text-center text-body">불러오고 있어요...</div>
  {:else if errorText || !job}
    <div class="text-center text-danger">{errorText ?? '데이터 없음'}</div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_420px] gap-8">
      <div class="flex flex-col gap-4">
        {#if videoError}
          <div class="card aspect-video flex items-center justify-center">
            <div class="text-center">
              <div class="text-body text-text-secondary-light dark:text-text-secondary-dark mb-3">
                영상 파일이 만료됐어요
              </div>
              <button
                type="button"
                on:click={reset}
                class="px-4 py-2 rounded-xl bg-brand text-white text-body font-medium hover:opacity-80 transition-opacity"
              >
                새로 만들기
              </button>
            </div>
          </div>
        {:else}
          <div class="card overflow-hidden aspect-video">
            <VideoPlayer
              bind:this={playerRef}
              bind:currentTime
              src={api.videoUrl(jobId)}
              vttSrc={api.vttUrl(jobId)}
              onError={() => (videoError = true)}
            />
          </div>
        {/if}
        <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
          {job.duration_sec?.toFixed(0) ?? '?'}초 · {job.language ?? '?'} · {job.model_name} · {segments.length}개 세그먼트
        </div>
        <DownloadBar {jobId} onBurnClick={handleBurnClick} onClipClick={() => (showClipSheet = true)} />
      </div>

      <aside class="card p-4 max-h-[calc(100vh-4rem)] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <div class="text-title">자막</div>
          <button
            type="button"
            class="text-caption text-text-secondary-light dark:text-text-secondary-dark hover:text-brand transition-colors"
            on:click={() => {
              const text = segments.map((s) => s.text).join('\n');
              const sl = job?.language || 'auto';
              const tl = sl === 'ko' ? 'en' : 'ko';
              window.open(
                `https://translate.google.com/?sl=${sl}&tl=${tl}&text=${encodeURIComponent(text)}&op=translate`,
                '_blank'
              );
            }}
          >🌐 전체 번역</button>
        </div>
        <SegmentList
          {jobId}
          {segments}
          bind:currentTime
          onJump={(t) => playerRef?.seekTo(t)}
          language={job?.language}
        />
      </aside>
    </div>
  {/if}
</div>

<BurnSheet
  open={showBurnSheet}
  {jobId}
  onClose={() => (showBurnSheet = false)}
/>

<ClipSheet
  open={showClipSheet}
  {jobId}
  durationSec={job?.duration_sec ?? 0}
  {currentTime}
  onClose={() => (showClipSheet = false)}
/>
