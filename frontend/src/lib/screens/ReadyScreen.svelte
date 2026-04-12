<script lang="ts">
  import { onMount } from 'svelte';

  import { api } from '$lib/api/jobs';
  import type { JobDto, SegmentDto } from '$lib/api/types';
  import DownloadBar from '$lib/ui/DownloadBar.svelte';
  import SearchReplace from '$lib/ui/SearchReplace.svelte';
  import SegmentList from '$lib/ui/SegmentList.svelte';
  import VideoPlayer from '$lib/ui/VideoPlayer.svelte';

  export let jobId: string;

  let job: JobDto | null = null;
  let segments: SegmentDto[] = [];
  let loading = true;
  let errorText: string | null = null;
  let playerRef: VideoPlayer | null = null;
  let currentTime = 0;
  let showSearch = false;
  let showBurnSheet = false;

  onMount(async () => {
    try {
      [job, segments] = await Promise.all([api.getJob(jobId), api.segments(jobId)]);
    } catch (e) {
      errorText = e instanceof Error ? e.message : '불러올 수 없어요';
    } finally {
      loading = false;
    }
  });

  async function handleBurnClick() {
    showBurnSheet = true;
    try {
      await api.triggerBurn(jobId);
    } catch {}
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
        <div class="card overflow-hidden aspect-video">
          <VideoPlayer
            bind:this={playerRef}
            bind:currentTime
            src={api.videoUrl(jobId)}
            vttSrc={api.vttUrl(jobId)}
          />
        </div>
        <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
          {job.duration_sec?.toFixed(0) ?? '?'}초 · {job.language ?? '?'} · {job.model_name} · {segments.length}개 세그먼트
        </div>
        <DownloadBar {jobId} onBurnClick={handleBurnClick} />
        {#if showBurnSheet}
          <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark">
            영상 인코딩 중이에요. 잠시 후 다운로드 링크가 준비됩니다.
          </div>
        {/if}
      </div>

      <aside class="card p-4 max-h-[calc(100vh-4rem)] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <div class="text-title">자막</div>
          <button
            type="button"
            class="text-caption text-brand"
            on:click={() => (showSearch = !showSearch)}
          >찾아 바꾸기</button>
        </div>
        {#if showSearch}
          <div class="mb-4">
            <SearchReplace
              {jobId}
              on:applied={async () => {
                segments = await api.segments(jobId);
              }}
            />
          </div>
        {/if}
        <SegmentList
          {jobId}
          {segments}
          bind:currentTime
          onJump={(t) => playerRef?.seekTo(t)}
        />
      </aside>
    </div>
  {/if}
</div>
