<script lang="ts">
  import { onMount } from 'svelte';

  import { api } from '$lib/api/jobs';
  import type { ConfigDto, ModelName } from '$lib/api/types';
  import { current } from '$lib/stores/current';
  import { pushHistory } from '$lib/stores/history';
  import Button from '$lib/ui/Button.svelte';
  import Input from '$lib/ui/Input.svelte';
  import Segmented from '$lib/ui/Segmented.svelte';

  let url = '';
  let model: string = 'small';
  let language = 'auto';
  let busy = false;
  let errorText: string | null = null;
  let config: ConfigDto | null = null;

  const languageOptions = [
    { value: 'auto', label: '자동 감지' },
    { value: 'ko', label: '한국어' },
    { value: 'en', label: 'English' },
    { value: 'ja', label: '日本語' },
    { value: 'zh', label: '中文' }
  ];

  onMount(async () => {
    try {
      config = await api.config();
      model = config.default_model;
    } catch {
      errorText = '서버에 연결할 수 없어요';
    }
  });

  $: modelOptions = (
    config?.available_models ?? (['tiny', 'base', 'small', 'medium', 'large-v3'] as ModelName[])
  ).map((m) => ({ value: m as string, label: m as string }));

  function setCurrentJobId(jobId: string) {
    (window as unknown as { __gensubCurrentJobId?: string }).__gensubCurrentJobId = jobId;
  }

  async function start() {
    if (!url.trim() || busy) return;
    busy = true;
    errorText = null;
    try {
      const res = await api.createJob({
        url: url.trim(),
        model: model as ModelName,
        language: language === 'auto' ? undefined : language
      });
      pushHistory({ jobId: res.job_id, title: null, createdAt: new Date().toISOString() });
      setCurrentJobId(res.job_id);
      current.set({
        screen: 'processing',
        job: null,
        progress: 0,
        stageMessage: '준비하고 있어요',
        errorMessage: null
      });
    } catch (e) {
      errorText = e instanceof Error ? e.message : '작업을 시작할 수 없어요';
    } finally {
      busy = false;
    }
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter') start();
  }
</script>

<div class="min-h-screen flex items-center justify-center px-6">
  <div class="w-full max-w-2xl flex flex-col gap-12">
    <h1 class="text-display text-center">
      자막 만들 영상 주소를<br />알려주세요
    </h1>

    <Input
      bind:value={url}
      type="url"
      placeholder="https://"
      autofocus
      on:keydown={handleKey}
    />

    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="flex items-center gap-3">
        <span class="text-caption text-text-secondary-light dark:text-text-secondary-dark">모델</span>
        <Segmented options={modelOptions} bind:value={model} />
      </div>
      <div class="flex items-center gap-3">
        <span class="text-caption text-text-secondary-light dark:text-text-secondary-dark">언어</span>
        <Segmented options={languageOptions} bind:value={language} />
      </div>
    </div>

    <Button variant="primary" fullWidth disabled={busy || !url.trim()} on:click={start}>
      {busy ? '시작하고 있어요...' : '자막 만들기'}
    </Button>

    {#if errorText}
      <div class="text-center text-caption text-danger">{errorText}</div>
    {/if}

    <div class="text-center text-caption text-text-secondary-light dark:text-text-secondary-dark">
      또는 파일을 여기로 드래그하세요
    </div>
  </div>
</div>
