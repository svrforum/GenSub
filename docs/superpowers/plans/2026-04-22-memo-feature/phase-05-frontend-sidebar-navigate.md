# Phase 5 — Frontend: 사이드바 탭 + MemoCard + 보러가기 seek

목표: 사이드바에 "영상/메모" 탭 추가, 전역 메모 리스트 UI, 메모 카드 클릭 → 해당 영상 이동 + 자동 seek.

**전제**: Phase 4 완료, `feature/memo` 브랜치.

---

### Task 5.1: MemoCard 컴포넌트

**Files:**
- Create: `frontend/src/lib/ui/MemoCard.svelte`

- [ ] **Step 1: 기존 카드 스타일 참고**

```bash
head -40 frontend/src/lib/ui/Sidebar.svelte
```

사이드바 내 작업 이력 카드의 패딩/타이포 패턴 확인.

- [ ] **Step 2: 컴포넌트 작성**

Write `frontend/src/lib/ui/MemoCard.svelte`:

```svelte
<script lang="ts">
 import { Trash2 } from 'lucide-svelte';

 import type { MemoListItemDto } from '$lib/api/types';

 export let memo: MemoListItemDto;
 export let onOpen: (memo: MemoListItemDto) => void;
 export let onDelete: (memoId: number) => void;

 let hovered = false;

 function fmtMMSS(sec: number): string {
 const total = Math.floor(sec);
 const m = Math.floor(total / 60);
 const s = total % 60;
 return `${m}:${s.toString().padStart(2, '0')}`;
 }

 function handleClick() {
 if (!memo.job_alive) return;
 onOpen(memo);
 }

 function handleDelete(e: MouseEvent) {
 e.stopPropagation();
 if (confirm('이 메모를 삭제할까요?')) {
 onDelete(memo.id);
 }
 }
</script>

<li
 class="relative rounded-lg px-3 py-2 transition-colors
 {memo.job_alive
 ? 'hover:bg-black/[0.04] dark:hover:bg-white/[0.04] cursor-pointer'
 : 'opacity-50 cursor-not-allowed'}"
 on:mouseenter={() => (hovered = true)}
 on:mouseleave={() => (hovered = false)}
 on:click={handleClick}
 on:keydown={(e) => (e.key === 'Enter' ? handleClick() : null)}
 role="button"
 tabindex={memo.job_alive ? 0 : -1}
>
 <div class="text-[12px] leading-snug text-text-primary-light dark:text-text-primary-dark line-clamp-2">
 {memo.segment_text}
 </div>

 {#if memo.memo_text}
 <div class="mt-1 text-[11px] leading-snug
 text-text-secondary-light dark:text-text-secondary-dark
 line-clamp-2">
 💭 {memo.memo_text}
 </div>
 {/if}

 <div class="mt-1.5 text-[10px] text-text-secondary-light dark:text-text-secondary-dark
 flex items-center gap-1.5">
 <span class="truncate">{memo.job_title ?? '(제목 없음)'}</span>
 <span>·</span>
 <span class="tabular-nums shrink-0">{fmtMMSS(memo.start)}</span>
 {#if !memo.job_alive}
 <span class="ml-auto px-1.5 py-0.5 rounded bg-text-secondary-light/10 text-[9px]">
 영상 삭제됨
 </span>
 {/if}
 </div>

 {#if hovered}
 <button
 type="button"
 on:click={handleDelete}
 class="absolute right-2 top-2 p-1 rounded
 text-text-secondary-light dark:text-text-secondary-dark
 hover:bg-danger/10 hover:text-danger transition-colors"
 aria-label="메모 삭제"
 >
 <Trash2 size={13} />
 </button>
 {/if}
</li>
```

- [ ] **Step 3: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/MemoCard.svelte
git commit -m "$(cat <<'EOF'
feat(memo): add MemoCard component

사이드바 메모 탭의 리스트 카드. 2줄 ellipsis segment_text,
옵션 메모_text(💭), 영상 제목 · MM:SS.

job_alive=false: opacity + "영상 삭제됨" 배지 + 클릭 비활성.
Hover 시 우상단에 삭제 버튼.
EOF
)"
```

---

### Task 5.2: Sidebar 탭 구조 추가

**Files:**
- Modify: `frontend/src/lib/ui/Sidebar.svelte`

- [ ] **Step 1: 현재 Sidebar 구조 파악**

```bash
wc -l frontend/src/lib/ui/Sidebar.svelte
grep -n "{#if\|{:else}\|{#each}" frontend/src/lib/ui/Sidebar.svelte | head -20
```

기존 nav(작업 이력) 영역의 열고 닫는 경계를 찾는다.

- [ ] **Step 2: Script 블록에 탭 상태 + memo 스토어 import 추가**

`<script>` 블록 상단(기존 import 근처)에 추가:

```ts
import { Video, Bookmark } from 'lucide-svelte';
import { memos, refreshMemos, removeMemoLocal } from '$lib/stores/memos';
import { memoApi } from '$lib/api/memo';
import { openMemo } from '$lib/stores/current';
import MemoCard from '$lib/ui/MemoCard.svelte';
import type { MemoListItemDto } from '$lib/api/types';

let sidebarTab: 'videos' | 'memos' = 'videos';
```

기존 onMount가 있으면 거기에 `refreshMemos()` 추가:
```ts
onMount(async () => {
 // 기존 로직 ...
 refreshMemos();
});
```

탭 변경 시 메모 탭 진입 시 refresh:
```ts
$: if (sidebarTab === 'memos' && !collapsed) {
 refreshMemos();
}
```

메모 핸들러:
```ts
async function handleOpenMemo(m: MemoListItemDto) {
 openMemo(m.job_id, m.start);
}

async function handleDeleteMemo(memoId: number) {
 removeMemoLocal(memoId);
 try {
 await memoApi.delete(memoId);
 } catch {
 refreshMemos(); // 실패 시 서버에서 다시
 }
}
```

- [ ] **Step 3: 템플릿에 탭 UI 추가**

기존 `<nav aria-label="작업 이력">` 을 감싸는 구조를 탭으로 분기. 예시 변경:

```svelte
<!-- 변경 전 패턴 (기존 위치):
<nav aria-label="작업 이력" class="...">
 <!-- 작업 이력 렌더링 -->
</nav>

변경 후: -->

<!-- 탭 헤더 -->
<div class="flex border-b border-black/5 dark:border-white/5 px-3">
 <button
 type="button"
 class="flex-1 py-2 text-[12px] font-medium flex items-center justify-center gap-1.5
 {sidebarTab === 'videos'
 ? 'text-brand border-b-2 border-brand'
 : 'text-text-secondary-light dark:text-text-secondary-dark hover:text-text-primary-light dark:hover:text-text-primary-dark'}"
 on:click={() => (sidebarTab = 'videos')}
 >
 <Video size={14} strokeWidth={1.75} />
 영상
 {#if $history.length > 0}
 <span class="text-[10px] opacity-70">{$history.length}</span>
 {/if}
 </button>
 <button
 type="button"
 class="flex-1 py-2 text-[12px] font-medium flex items-center justify-center gap-1.5
 {sidebarTab === 'memos'
 ? 'text-brand border-b-2 border-brand'
 : 'text-text-secondary-light dark:text-text-secondary-dark hover:text-text-primary-light dark:hover:text-text-primary-dark'}"
 on:click={() => (sidebarTab = 'memos')}
 >
 <Bookmark size={14} strokeWidth={1.75} />
 메모
 {#if $memos.length > 0}
 <span class="text-[10px] opacity-70">{$memos.length}</span>
 {/if}
 </button>
</div>

<!-- 탭 콘텐츠 -->
{#if sidebarTab === 'videos'}
 <nav aria-label="작업 이력" class="flex-1 overflow-y-auto">
 <!-- 기존 작업 이력 렌더링 블록을 그대로 이 안에 유지 -->
 ...
 </nav>
{:else}
 <nav aria-label="저장한 메모" class="flex-1 overflow-y-auto px-2 py-2">
 {#if $memos.length === 0}
 <div class="text-[13px] text-text-secondary-light dark:text-text-secondary-dark
 px-3 py-6 text-center">
 아직 저장한 문장이 없어요.
 <br />
 자막 오른쪽 📎 로 저장해 보세요.
 </div>
 {:else}
 <ul class="space-y-1">
 {#each $memos as memo (memo.id)}
 <MemoCard
 {memo}
 onOpen={handleOpenMemo}
 onDelete={handleDeleteMemo}
 />
 {/each}
 </ul>
 {/if}
 </nav>
{/if}
```

**주의**:
- 탭 영역은 기존 `작업은 24시간 후...` 푸터 **위**, 헤더 아래에 배치.
- 기존 `영상 탭 내용`(작업 이력)은 절대 건드리지 않는다 — 그대로 `{#if sidebarTab === 'videos'}` 안에 감싼다.

- [ ] **Step 4: 타입체크 + 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -10
npm run build 2>&1 | tail -5
```

Expected: 0 errors, 빌드 성공.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/Sidebar.svelte
git commit -m "$(cat <<'EOF'
feat(memo): add sidebar tabs (영상 / 메모) with count badges

스펙 §5.1 Q2-A:
- 사이드바 상단에 Video / Bookmark 아이콘 탭
- 영상 탭: 기존 작업 이력 그대로 (무변경)
- 메모 탭: refreshMemos() 자동 호출, MemoCard 리스트
- 빈 상태 문구: "아직 저장한 문장이 없어요"
- 메모 카드 클릭 → openMemo(jobId, start) 호출
EOF
)"
```

---

### Task 5.3: Job 삭제 다이얼로그에 메모 개수 경고

**Files:**
- Modify: `frontend/src/lib/ui/Sidebar.svelte` (`confirmDelete` 수정)

- [ ] **Step 1: 현재 confirmDelete 확인**

```bash
grep -n "confirmDelete\|이 작업\|함께 삭제" frontend/src/lib/ui/Sidebar.svelte
```

기존 다이얼로그 문구: `"<name>"을(를) 삭제할까요?\n영상과 자막 파일도 함께 삭제돼요.`

- [ ] **Step 2: 메모 개수 조회 + 문구 확장**

Edit `confirmDelete`:

```ts
async function confirmDelete(item: HistoryItem) {
 const name = item.title || '이 작업';
 let memoCount = 0;
 try {
 const res = await memoApi.listForJob(item.jobId);
 memoCount = res.items.length;
 } catch {
 // 무시, 0으로 진행
 }

 const memoLine = memoCount > 0
 ? `\n이 영상에 저장한 메모 ${memoCount}개도 함께 삭제됩니다.`
 : '';

 if (!confirm(`"${name}"을(를) 삭제할까요?\n영상과 자막 파일도 함께 삭제돼요.${memoLine}`)) {
 return;
 }

 try {
 await api.deleteJob(item.jobId);
 } catch {
 // 이미 삭제된 경우 무시
 }
 removeFromHistory(item.jobId);
 if ($current.jobId === item.jobId) reset();
 if (memoCount > 0) {
 refreshMemos(); // 전역 메모 리스트에서 제거됨
 }
}
```

`memoApi` 는 이미 Task 5.2에서 import됨. `refreshMemos` 도 동일.

- [ ] **Step 3: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/Sidebar.svelte
git commit -m "$(cat <<'EOF'
feat(memo): warn about memo count in job delete dialog

Job 삭제 확인 다이얼로그에 "이 영상의 메모 N개도 함께 삭제됩니다"
추가 (메모가 있을 때만). 스펙 §4.5.

삭제 성공 시 refreshMemos로 전역 리스트에서도 제거됨 반영.
EOF
)"
```

---

### Task 5.4: VideoPlayer에 `onLoadedMetadata` 노출

**Files:**
- Modify: `frontend/src/lib/ui/VideoPlayer.svelte`

- [ ] **Step 1: 현재 VideoPlayer 파악**

```bash
cat frontend/src/lib/ui/VideoPlayer.svelte
```

현재 props와 이벤트 확인.

- [ ] **Step 2: onLoadedMetadata prop 추가**

Edit VideoPlayer.svelte:

```ts
// <script> 블록 props에 추가:
export let onLoadedMetadata: (() => void) | null = null;
```

`<video>` 태그에 바인드:
```svelte
<video
 bind:this={videoEl}
 on:loadedmetadata={() => onLoadedMetadata?.()}
 ... 기존 속성들 ...
>
```

`seekTo` 함수가 이미 있다면 유지. 없으면 추가:
```ts
export function seekTo(seconds: number): void {
 if (videoEl) {
 videoEl.currentTime = seconds;
 }
}
```

- [ ] **Step 3: 타입체크 + 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/VideoPlayer.svelte
git commit -m "$(cat <<'EOF'
feat(memo): expose onLoadedMetadata callback on VideoPlayer

ReadyScreen이 loadedmetadata 이벤트 후에만 seekTo를 호출하도록
콜백 노출. seek before load 실패 방지.
EOF
)"
```

---

### Task 5.5: ReadyScreen에서 `initialTime` reactive seek

**Files:**
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte`

스펙 §5.4의 reactive 블록 하나로 초기 마운트 + 같은 Job 재방문(initialTime 변경) 모두 처리.

- [ ] **Step 1: 현재 ReadyScreen 구조 확인**

```bash
head -60 frontend/src/lib/screens/ReadyScreen.svelte
```

- [ ] **Step 2: `initialTime` 소비 로직 추가**

Edit `frontend/src/lib/screens/ReadyScreen.svelte`:

1. `<script>` 상단 import 추가:
 ```ts
 import { current } from '$lib/stores/current';
 ```
 (이미 있으면 skip.)

2. state 선언부에 추가:
 ```ts
 let videoReady = false;
 let lastSeekTarget: number | null = null;
 ```

3. reactive 블록 추가 (기존 onMount 밖, script 하단):
 ```ts
 $: if (
 $current.initialTime !== undefined
 && $current.initialTime !== lastSeekTarget
 && playerRef
 && videoReady
 ) {
 playerRef.seekTo($current.initialTime);
 lastSeekTarget = $current.initialTime;
 }
 ```

4. `<VideoPlayer>` 태그에 `onLoadedMetadata` 프롭 전달:
 ```svelte
 <VideoPlayer
 bind:this={playerRef}
 bind:currentTime
 src={api.videoUrl(jobId)}
 vttSrc={api.vttUrl(jobId)}
 onError={() => (videoError = true)}
 onLoadedMetadata={() => (videoReady = true)}
 />
 ```

- [ ] **Step 3: 타입체크 + 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "$(cat <<'EOF'
feat(memo): reactive seek on current.initialTime change

스펙 §5.4:
- videoReady flag on loadedmetadata
- reactive 블록 하나로 초기 seek + 같은 Job 재방문 seek 모두 처리
- lastSeekTarget 가드로 중복 실행 방지

메모 "보러가기" 클릭 → current.initialTime 세팅 → 자동 seek.
EOF
)"
```

---

### Phase 5 완료 검증

- [ ] **Step 1: 프론트 빌드**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 2: 백엔드 회귀**

```bash
cd ../backend
uv run pytest --tb=short 2>&1 | tail -3
```

Expected: 141 passed (변경 없으니 그대로).

- [ ] **Step 3: 커밋 현황**

```bash
cd /Users/loki/GenSub
git log --oneline feature/memo ^master | cat
```

Expected: 19개 커밋 (1·2·3·4 14개 + 5의 5개).

Phase 5 완료. **기능 전체 구현 완료.** Phase 6은 통합 검증 + 머지.
