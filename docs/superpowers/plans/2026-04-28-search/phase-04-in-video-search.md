# Phase 4 — Frontend: 영상 내 ⌘F 오버레이 + 매치 하이라이트

목표: ReadyScreen 안에서 ⌘F 누르면 자막 검색 오버레이가 떠서 현재 영상의 segments를 필터·점프할 수 있게 한다. 클라이언트 사이드 only.

**전제**: Phase 3 완료, `feature/search` 브랜치.

---

### Task 4.1: InVideoSearchOverlay 컴포넌트

**Files:**
- Create: `frontend/src/lib/ui/InVideoSearchOverlay.svelte`

- [ ] **Step 1: 컴포넌트 작성**

Write `frontend/src/lib/ui/InVideoSearchOverlay.svelte`:

```svelte
<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Search, X, ChevronUp, ChevronDown } from 'lucide-svelte';

  import type { SegmentDto } from '$lib/api/types';

  /** 현재 영상의 모든 세그먼트. 이 배열로 클라이언트 매치 수행. */
  export let segments: SegmentDto[] = [];

  /** 매치된 세그먼트 클릭/Enter 시 호출. */
  export let onJump: (segment: SegmentDto) => void = () => {};

  /** 부모가 inputEl 에 포커스 / 오버레이 close 제어할 수 있게. */
  export let open = false;

  let inputEl: HTMLInputElement | null = null;
  let query = '';

  $: matches = computeMatches(segments, query);
  $: matchCount = matches.length;

  let currentIdx = 0;

  $: if (open && inputEl) {
    queueMicrotask(() => inputEl?.focus());
  }

  $: if (matches.length > 0 && currentIdx >= matches.length) {
    currentIdx = 0;
  }

  function computeMatches(segs: SegmentDto[], q: string): SegmentDto[] {
    const trimmed = q.trim().toLowerCase();
    if (!trimmed) return [];
    return segs.filter((s) => s.text.toLowerCase().includes(trimmed));
  }

  function gotoMatch(direction: 1 | -1) {
    if (matches.length === 0) return;
    currentIdx = (currentIdx + direction + matches.length) % matches.length;
    onJump(matches[currentIdx]);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) gotoMatch(-1);
      else gotoMatch(1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      gotoMatch(-1);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      gotoMatch(1);
    }
  }

  function close() {
    open = false;
    query = '';
    currentIdx = 0;
  }

  /** 부모에서 매치 정보를 받을 수 있도록 export. */
  export function getMatchedIdxSet(): Set<number> {
    return new Set(matches.map((m) => m.idx));
  }

  export function getCurrentMatchIdx(): number | null {
    return matches[currentIdx]?.idx ?? null;
  }

  onDestroy(() => {
    // nothing — open 은 부모가 관리
  });
</script>

{#if open}
  <div
    class="absolute top-2 right-2 z-20 flex items-center gap-2
           bg-white dark:bg-[#1c1c1e]
           border border-black/[0.08] dark:border-white/[0.1]
           rounded-xl shadow-lg
           px-2 py-1.5"
  >
    <Search size={14} strokeWidth={1.75}
            class="text-text-secondary-light dark:text-text-secondary-dark shrink-0" />
    <input
      bind:this={inputEl}
      bind:value={query}
      on:keydown={handleKey}
      type="text"
      placeholder="이 영상에서 검색…"
      class="w-48 bg-transparent border-0 outline-none text-[13px]
             text-text-primary-light dark:text-text-primary-dark
             placeholder:text-text-secondary-light dark:placeholder:text-text-secondary-dark"
    />
    <span class="shrink-0 text-[11px] text-text-secondary-light dark:text-text-secondary-dark tabular-nums">
      {#if query.trim() === ''}
        &nbsp;
      {:else if matchCount === 0}
        0
      {:else}
        {currentIdx + 1}/{matchCount}
      {/if}
    </span>
    <button
      type="button"
      on:click={() => gotoMatch(-1)}
      disabled={matchCount === 0}
      class="p-1 rounded hover:bg-black/[0.04] dark:hover:bg-white/[0.06]
             text-text-secondary-light dark:text-text-secondary-dark
             disabled:opacity-30 disabled:hover:bg-transparent"
      aria-label="이전 매치"
    >
      <ChevronUp size={14} strokeWidth={1.75} />
    </button>
    <button
      type="button"
      on:click={() => gotoMatch(1)}
      disabled={matchCount === 0}
      class="p-1 rounded hover:bg-black/[0.04] dark:hover:bg-white/[0.06]
             text-text-secondary-light dark:text-text-secondary-dark
             disabled:opacity-30 disabled:hover:bg-transparent"
      aria-label="다음 매치"
    >
      <ChevronDown size={14} strokeWidth={1.75} />
    </button>
    <button
      type="button"
      on:click={close}
      class="p-1 rounded hover:bg-black/[0.04] dark:hover:bg-white/[0.06]
             text-text-secondary-light dark:text-text-secondary-dark"
      aria-label="검색 닫기"
    >
      <X size={14} strokeWidth={1.75} />
    </button>
  </div>
{/if}
```

- [ ] **Step 2: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/InVideoSearchOverlay.svelte
git commit -m "feat(search): add InVideoSearchOverlay component (in-video ⌘F)

스펙 §5.5: ReadyScreen 안에서만 활성화되는 자막 필터.
- 절대좌표 top-2 right-2, 작은 카드 형태
- query 입력 → segments 배열 클라이언트 필터 (toLowerCase().includes)
- N/M 카운트 표시
- Enter / ArrowDown → 다음, Shift+Enter / ArrowUp → 이전
- Esc → close
- onJump callback 으로 부모가 영상 seek + 스크롤 처리

API 안 부름. ReadyScreen 이 이미 segments 배열 들고 있어 즉시 매치."
```

---

### Task 4.2: SegmentList 매치 하이라이트 prop 지원

**Files:**
- Modify: `frontend/src/lib/ui/SegmentList.svelte`

- [ ] **Step 1: SegmentList prop 추가**

`frontend/src/lib/ui/SegmentList.svelte` 의 `<script>` 영역에 props 추가:

```ts
/** 검색 매치된 segment idx 집합. 노란 배경 강조. */
export let matchedIdxs: Set<number> = new Set();

/** 현재 활성 매치 segment idx. 더 진한 강조. */
export let currentMatchIdx: number | null = null;
```

각 segment 카드 렌더링 부분에 매치 강조 클래스 추가. 기존 카드의 className 에 다음 조건부 추가:

```svelte
class="기존 클래스 ...
       {matchedIdxs.has(segment.idx) ? 'ring-2 ring-yellow-400/40' : ''}
       {currentMatchIdx === segment.idx ? 'bg-yellow-400/15 ring-yellow-500/60' : ''}"
```

(SegmentList 의 정확한 카드 구조에 맞춰 위치 조정 — 기존 active job hover 효과와 충돌하지 않게.)

scrollIntoView: `currentMatchIdx` 변경 reactive 블록 추가:

```ts
$: if (currentMatchIdx !== null) {
  queueMicrotask(() => {
    const el = document.querySelector(`[data-segment-idx="${currentMatchIdx}"]`);
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  });
}
```

각 segment 카드 element 에 `data-segment-idx={segment.idx}` 추가.

- [ ] **Step 2: 타입체크**

```bash
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/SegmentList.svelte
git commit -m "feat(search): add match highlight props to SegmentList

새 props: matchedIdxs (Set<number>), currentMatchIdx (number | null).
- matchedIdxs 에 든 segment 는 노란 ring 강조
- currentMatchIdx 는 더 진한 배경 + ring
- currentMatchIdx 변경 시 자동 scrollIntoView (block: 'center')
- 각 카드에 data-segment-idx 속성 추가 (스크롤 타깃)

InVideoSearchOverlay 와 함께 사용."
```

---

### Task 4.3: ReadyScreen에 ⌘F 핸들러 + 오버레이 통합

**Files:**
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte`

- [ ] **Step 1: 현재 ReadyScreen 확인**

```bash
cd /Users/loki/GenSub
cat frontend/src/lib/screens/ReadyScreen.svelte | head -40
```

기존 onMount/onDestroy 패턴 확인.

- [ ] **Step 2: ⌘F 캡처 + 오버레이 + SegmentList 연결**

Edit `frontend/src/lib/screens/ReadyScreen.svelte`:

import 추가 (`<script>` 상단):

```ts
import InVideoSearchOverlay from '$lib/ui/InVideoSearchOverlay.svelte';
import type { SegmentDto } from '$lib/api/types';
```

state 추가:

```ts
let inVideoSearchOpen = false;
let overlayRef: InVideoSearchOverlay | null = null;
let matchedIdxs: Set<number> = new Set();
let currentMatchIdx: number | null = null;
```

⌘F 캡처 핸들러를 `onMount` 안에 추가 (기존 핸들러 옆에):

```ts
function handleSearchKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
    e.preventDefault();
    inVideoSearchOpen = true;
  }
}

onMount(() => {
  // 기존 onMount 로직 ...
  window.addEventListener('keydown', handleSearchKey);
  return () => window.removeEventListener('keydown', handleSearchKey);
});
```

(만약 기존 onMount 가 두 개로 나뉘어 있다면 적절한 곳에 합쳐 넣는다.)

매치 점프 핸들러:

```ts
function handleInVideoJump(seg: SegmentDto) {
  playerRef?.seekTo(seg.start);
  // 매치 정보 갱신
  if (overlayRef) {
    matchedIdxs = overlayRef.getMatchedIdxSet();
    currentMatchIdx = overlayRef.getCurrentMatchIdx();
  }
}
```

`{#if !loading && !errorText && job}` 블록 안 (player+segments 영역) 끝나는 곳에 오버레이 + SegmentList 수정:

```svelte
<div class="relative">
  <InVideoSearchOverlay
    bind:this={overlayRef}
    bind:open={inVideoSearchOpen}
    {segments}
    onJump={handleInVideoJump}
  />
  <!-- 기존 player + downloadbar -->
</div>

<SegmentList
  {jobId}
  {segments}
  bind:currentTime
  onJump={(t) => playerRef?.seekTo(t)}
  language={job?.language}
  {matchedIdxs}
  {currentMatchIdx}
/>
```

(InVideoSearchOverlay 가 absolute 라 부모가 relative 여야 함. 기존 player 영역의 부모 div에 `relative` 추가.)

오버레이가 close 될 때 매치 강조도 해제:

```ts
$: if (!inVideoSearchOpen) {
  matchedIdxs = new Set();
  currentMatchIdx = null;
}
```

- [ ] **Step 3: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -10
```

Expected: 0 errors.

- [ ] **Step 4: 빌드**

```bash
npm run build 2>&1 | tail -5
```

Expected: 빌드 성공.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "feat(search): integrate ⌘F overlay into ReadyScreen

스펙 §5.5:
- 페이지 mount 시 window keydown 리스너로 ⌘F/Ctrl+F 캡처
  (브라우저 기본 검색 차단)
- InVideoSearchOverlay 렌더, segments + onJump prop 전달
- onJump 콜백에서 playerRef.seekTo + matchedIdxs/currentMatchIdx 갱신
- SegmentList 에 매치 정보 prop 전달 → 노란 강조
- 오버레이 close 시 매치 강조 자동 해제 (reactive)"
```

---

### Phase 4 완료 검증

- [ ] **Step 1: 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

Expected: 0 errors, 빌드 OK.

- [ ] **Step 2: 단축키 충돌 점검**

`+layout.svelte` 의 ⌘K 핸들러와 `ReadyScreen` 의 ⌘F 핸들러가 둘 다 `window` 에 등록됨. ⌘K 와 ⌘F 는 키가 달라서 충돌 없음. 단, 모달이 열려있는 상태에서 ⌘F 를 누르면 어떻게 될지 한 번 생각:
- SearchModal 이 `searchOpen=true` 일 때 input 에 포커스 → 사용자가 거기서 ⌘F → ReadyScreen 핸들러도 fire? Yes.
- 사용자 의도가 모호한 케이스라 v1 에선 그대로 둠. 두 오버레이가 동시에 보일 수 있지만 z-index 가 다르고 닫기는 Esc 로 가능.

기록만 남기고 다음으로:

- [ ] **Step 3: 커밋 로그**

```bash
cd /Users/loki/GenSub
git log --oneline feature/search ^master | cat
```

Expected: 11 커밋 (Phase 1 의 2 + Phase 2 의 3 + Phase 3 의 3 + Phase 4 의 3).

Phase 4 완료. Phase 5 (검증 + 머지) 진행.
