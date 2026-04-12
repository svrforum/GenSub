<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  import { api } from '$lib/api/jobs';
  import { subscribeJobEvents } from '$lib/api/events';
  import { current, reset } from '$lib/stores/current';
  import Button from '$lib/ui/Button.svelte';
  import CircularProgress from '$lib/ui/CircularProgress.svelte';

  export let jobId: string;

  let unsubscribe: (() => void) | null = null;
  let title = '';

  const stageCopy: Record<string, string> = {
    pending: '준비하고 있어요',
    downloading: '영상을 가져오고 있어요',
    transcribing: '음성을 듣고 있어요',
    burning: '자막을 영상에 입히고 있어요'
  };

  const rotatingCopy: Record<string, string[]> = {
    pending: ['준비하고 있어요', '잠시만요'],
    downloading: ['영상을 가져오고 있어요', '네트워크에서 받는 중이에요', '거의 다 왔어요'],
    transcribing: [
      '음성을 듣고 있어요',
      '단어를 받아쓰고 있어요',
      '타임스탬프를 맞추고 있어요'
    ],
    burning: [
      '자막을 영상에 입히고 있어요',
      '프레임마다 자막을 그리고 있어요',
      '거의 끝났어요'
    ]
  };

  let rotationTimer: ReturnType<typeof setInterval> | null = null;
  let rotationIdx = 0;

  function applyRotatingCopy(status: string) {
    const arr = rotatingCopy[status];
    if (!arr) return;
    current.update((c) => ({ ...c, stageMessage: arr[rotationIdx % arr.length] }));
  }

  onMount(async () => {
    try {
      const job = await api.getJob(jobId);
      title = job.title ?? job.source_url ?? '';
      current.update((c) => ({
        ...c,
        job,
        stageMessage: stageCopy[job.status] ?? c.stageMessage
      }));
    } catch {
      /* job may have been deleted */
    }

    unsubscribe = subscribeJobEvents(jobId, {
      onProgress(evt) {
        rotationIdx = 0;
        current.update((c) => ({
          ...c,
          progress: evt.progress,
          stageMessage: evt.stage_message ?? stageCopy[evt.status] ?? c.stageMessage,
          job: c.job ? { ...c.job, status: evt.status } : c.job
        }));
      },
      onDone(status) {
        if (status === 'ready' || status === 'done') {
          current.update((c) => ({ ...c, screen: 'ready', progress: 1 }));
        }
      },
      onError(message) {
        current.update((c) => ({ ...c, screen: 'error', errorMessage: message }));
      }
    });

    rotationTimer = setInterval(() => {
      rotationIdx += 1;
      const st = $current.job?.status ?? 'pending';
      applyRotatingCopy(st);
    }, 10000);
  });

  onDestroy(() => {
    unsubscribe?.();
    if (rotationTimer) clearInterval(rotationTimer);
  });

  async function cancel() {
    try {
      await api.cancelJob(jobId);
    } catch {
      /* best effort */
    }
    reset();
  }
</script>

<div class="min-h-screen flex items-center justify-center px-6">
  <div class="flex flex-col items-center gap-12 max-w-md w-full">
    {#if title}
      <div class="card px-6 py-4 w-full text-center">
        <div class="text-body font-semibold truncate">{title}</div>
      </div>
    {/if}

    <CircularProgress value={$current.progress} />

    <div class="text-center">
      <div class="text-title">{$current.stageMessage}</div>
    </div>

    <Button variant="ghost" on:click={cancel}>취소</Button>
  </div>
</div>
