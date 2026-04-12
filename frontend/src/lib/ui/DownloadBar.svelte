<script lang="ts">
  import { api } from '$lib/api/jobs';
  import Button from '$lib/ui/Button.svelte';

  export let jobId: string;
  export let onBurnClick: () => void = () => {};
</script>

<div class="flex flex-wrap items-center gap-2">
  <a class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
     href={api.srtUrl(jobId)} download>.srt</a>
  <a class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
     href={api.vttUrl(jobId)} download>.vtt</a>
  <a class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
     href={api.txtUrl(jobId)} download>.txt</a>
  <a class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
     href={api.jsonUrl(jobId)} download>.json</a>
  <a class="px-3 py-2 rounded-badge bg-divider-light dark:bg-surface-dark-elevated text-caption"
     href={api.mkvUrl(jobId)} download>.mkv</a>
  <div class="ml-auto">
    <Button variant="primary" on:click={onBurnClick}>영상에 구워서 다운로드</Button>
  </div>
</div>
