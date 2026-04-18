<script lang="ts">
  import { api } from '$lib/api/jobs';
  import { current } from '$lib/stores/current';
  import Button from '$lib/ui/Button.svelte';

  export let jobId: string;
</script>

<div class="min-h-screen flex items-center justify-center px-6">
  <div class="max-w-md flex flex-col items-center gap-8 text-center">
    <div class="text-display">완료됐어요</div>
    <div class="text-body text-text-secondary-light dark:text-text-secondary-dark">
      자막이 영상에 입혀진 mp4 파일이 준비됐어요
    </div>
    <a class="w-full" href={api.burnedUrl(jobId)} download>
      <Button variant="primary" fullWidth>다운로드</Button>
    </a>
    <Button
      variant="ghost"
      on:click={() => current.update((c) => ({ ...c, screen: 'ready' }))}
    >편집기로 돌아가기</Button>
  </div>
</div>
