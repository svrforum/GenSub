# Phase 10 — Idle Screen (Step 1)

URL 입력 화면. Toss × Apple 디자인 언어에 따라 **하나의 큰 입력 필드**에 집중하고, 주변은 의도적으로 비운다.

**사전 조건**: Phase 8-9 완료.

---

### Task 10.1: Idle 화면 기본 구조

**Files:**
- Create: `frontend/src/lib/screens/IdleScreen.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: IdleScreen 작성**

Write `frontend/src/lib/screens/IdleScreen.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import Button from '$lib/ui/Button.svelte';
  import Input from '$lib/ui/Input.svelte';
  import Segmented from '$lib/ui/Segmented.svelte';
  import { api } from '$lib/api/jobs';
  import type { ConfigDto, ModelName } from '$lib/api/types';
  import { current } from '$lib/stores/current';
  import { pushHistory } from '$lib/stores/history';

  let url = '';
  let model: ModelName = 'small';
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
    } catch (e) {
      errorText = '서버에 연결할 수 없어요';
    }
  });

  $: modelOptions = (config?.available_models ?? ['tiny', 'base', 'small', 'medium', 'large-v3']).map(
    (m) => ({ value: m, label: m })
  );

  async function start() {
    if (!url.trim() || busy) return;
    busy = true;
    errorText = null;
    try {
      const res = await api.createJob({
        url: url.trim(),
        model,
        language: language === 'auto' ? undefined : language
      });
      pushHistory({ jobId: res.job_id, title: null, createdAt: new Date().toISOString() });
      current.set({
        screen: 'processing',
        job: null,
        progress: 0,
        stageMessage: '준비하고 있어요',
        errorMessage: null
      });
      // 화면 전환은 +page.svelte가 current store를 감시해 수행
      const { jobId: _jid } = { jobId: res.job_id };
      (window as any).__gensubCurrentJobId = res.job_id;
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
```

- [ ] **Step 2: +page.svelte에서 screen store 기반 분기**

Overwrite `frontend/src/routes/+page.svelte`:

```svelte
<script lang="ts">
  import { current } from '$lib/stores/current';
  import IdleScreen from '$lib/screens/IdleScreen.svelte';
</script>

{#if $current.screen === 'idle'}
  <IdleScreen />
{:else}
  <!-- Processing / Ready / Error screens는 Phase 11+ 에서 추가 -->
  <div class="min-h-screen flex items-center justify-center">
    <p class="text-body text-text-secondary-light dark:text-text-secondary-dark">
      화면: {$current.screen}
    </p>
  </div>
{/if}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/IdleScreen.svelte frontend/src/routes/+page.svelte
git commit -m "feat(frontend): add IdleScreen with URL input and options"
```

---

### Task 10.2: 파일 드래그 앤 드롭

**Files:**
- Modify: `frontend/src/lib/screens/IdleScreen.svelte`

- [ ] **Step 1: 드래그/드롭 핸들러 추가**

Modify `frontend/src/lib/screens/IdleScreen.svelte`: `script` 블록 하단에 다음 함수 추가:

```typescript
let dragActive = false;

function onDragOver(e: DragEvent) {
  e.preventDefault();
  dragActive = true;
}

function onDragLeave() {
  dragActive = false;
}

async function onDrop(e: DragEvent) {
  e.preventDefault();
  dragActive = false;
  const file = e.dataTransfer?.files[0];
  if (!file) return;
  busy = true;
  errorText = null;
  try {
    const res = await api.uploadJob(file, model, language === 'auto' ? undefined : language);
    pushHistory({ jobId: res.job_id, title: file.name, createdAt: new Date().toISOString() });
    (window as any).__gensubCurrentJobId = res.job_id;
    current.set({
      screen: 'processing',
      job: null,
      progress: 0,
      stageMessage: '준비하고 있어요',
      errorMessage: null
    });
  } catch (e) {
    errorText = e instanceof Error ? e.message : '업로드 실패';
  } finally {
    busy = false;
  }
}
```

그리고 최상위 `<div>`에 이벤트 리스너를 추가하고 드래그 상태를 반영하도록 수정:

```svelte
<div
  class="min-h-screen flex items-center justify-center px-6 transition-colors
         {dragActive ? 'bg-brand/5' : ''}"
  on:dragover={onDragOver}
  on:dragleave={onDragLeave}
  on:drop={onDrop}
>
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/IdleScreen.svelte
git commit -m "feat(frontend): support file drag-and-drop on idle screen"
```

---
