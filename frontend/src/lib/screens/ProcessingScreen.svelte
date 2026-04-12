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

  interface Sample {
    t: number;
    p: number;
  }
  let samples: Sample[] = [];
  let etaSec: number | null = null;

  function pushSample(progress: number) {
    const t = Date.now();
    samples = [...samples, { t, p: progress }].slice(-6);
    if (samples.length < 2) {
      etaSec = null;
      return;
    }
    const first = samples[0];
    const last = samples[samples.length - 1];
    const dp = last.p - first.p;
    const dt = (last.t - first.t) / 1000;
    if (dp <= 0 || dt <= 0) {
      etaSec = null;
      return;
    }
    const remaining = Math.max(0, 1 - last.p);
    etaSec = Math.round(remaining / (dp / dt));
  }

  function formatEta(secs: number | null): string | null {
    if (secs == null || !isFinite(secs) || secs < 0) return null;
    if (secs < 60) return `${secs}초 남았어요`;
    const mins = Math.round(secs / 60);
    return `${mins}분 남았어요`;
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
        current.update((c) => {
          if (c.job && c.job.status !== evt.status) {
            samples = [];
          }
          return {
            ...c,
            progress: evt.progress,
            stageMessage: evt.stage_message ?? stageCopy[evt.status] ?? c.stageMessage,
            job: c.job ? { ...c.job, status: evt.status } : c.job
          };
        });
        rotationIdx = 0;
        pushSample(evt.progress);
      },
      onDone(status) {
        if (status === 'done') {
          current.update((c) => ({ ...c, screen: 'burn_done', progress: 1 }));
        } else if (status === 'ready') {
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
      {#if formatEta(etaSec)}
        <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mt-2">
          {formatEta(etaSec)}
        </div>
      {/if}
    </div>

    <Button variant="ghost" on:click={cancel}>취소</Button>
  </div>
</div>
