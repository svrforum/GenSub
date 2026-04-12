<script lang="ts">
  import { api } from '$lib/api/jobs';
  import { current } from '$lib/stores/current';
  import BottomSheet from '$lib/ui/BottomSheet.svelte';
  import Button from '$lib/ui/Button.svelte';
  import Segmented from '$lib/ui/Segmented.svelte';

  export let open = false;
  export let jobId: string;
  export let onClose: () => void = () => {};

  let size: string = '42';
  let outline = true;

  const sizeOptions = [
    { value: '32', label: '작게' },
    { value: '42', label: '중간' },
    { value: '54', label: '크게' }
  ];

  async function start() {
    try {
      await api.triggerBurn(jobId, { size: parseInt(size, 10), outline });
      onClose();
      current.set({
        screen: 'processing',
        job: null,
        progress: 0,
        stageMessage: '자막을 영상에 입히고 있어요',
        errorMessage: null
      });
    } catch {}
  }
</script>

<BottomSheet {open} {onClose}>
  <div class="flex flex-col gap-6 py-2">
    <div>
      <div class="text-title">자막을 영상에 입힐게요</div>
      <div class="text-caption text-text-secondary-light dark:text-text-secondary-dark mt-1">
        영상 길이에 따라 수 분 정도 걸려요
      </div>
    </div>

    <div class="flex items-center justify-between">
      <span class="text-body">크기</span>
      <Segmented options={sizeOptions} bind:value={size} />
    </div>

    <label class="flex items-center justify-between text-body">
      <span>외곽선</span>
      <input type="checkbox" bind:checked={outline} class="w-12 h-7 rounded-full" />
    </label>

    <Button variant="primary" fullWidth on:click={start}>시작하기</Button>
    <Button variant="ghost" fullWidth on:click={onClose}>취소</Button>
  </div>
</BottomSheet>
