# Phase 4 — Frontend: SegmentMemo (저장 버튼 + 인라인 메모)

목표: ReadyScreen의 `SegmentList` 안 각 세그먼트에 📎 저장 버튼과 메모 입력 UI를 붙인다. Job 진입 시 해당 영상의 메모를 fetch, 409 충돌 시 확인 다이얼로그 처리.

**전제**: Phase 3 완료, 프론트 빌드 OK, `feature/memo` 브랜치.

---

### Task 4.1: 세그먼트별 메모 상태 조회 + 스토어

**Files:**
- Create: `frontend/src/lib/stores/jobMemos.ts`

ReadyScreen이 마운트될 때 `/api/jobs/{id}/memos` 를 fetch해서 "이 Job의 어느 segment가 저장돼 있는지" 를 작은 스토어로 유지. SegmentMemo 컴포넌트가 이 스토어로 자신의 상태를 판단.

- [ ] **Step 1: 스토어 작성**

Write `frontend/src/lib/stores/jobMemos.ts`:

```ts
import { writable } from 'svelte/store';

import { memoApi } from '$lib/api/memo';
import type { JobMemoLiteDto } from '$lib/api/types';

/** segment_idx -> memo lite 매핑. O(1) 조회. */
export const jobMemos = writable<Map<number, JobMemoLiteDto>>(new Map());

let currentJobId: string | null = null;

export async function loadJobMemos(jobId: string): Promise<void> {
 if (currentJobId === jobId) return;
 currentJobId = jobId;
 try {
 const res = await memoApi.listForJob(jobId);
 const map = new Map<number, JobMemoLiteDto>();
 for (const m of res.items) {
 map.set(m.segment_idx, m);
 }
 jobMemos.set(map);
 } catch {
 jobMemos.set(new Map());
 }
}

export function clearJobMemos(): void {
 currentJobId = null;
 jobMemos.set(new Map());
}

export function setJobMemo(memo: JobMemoLiteDto): void {
 jobMemos.update((m) => {
 const next = new Map(m);
 next.set(memo.segment_idx, memo);
 return next;
 });
}

export function unsetJobMemo(segmentIdx: number): void {
 jobMemos.update((m) => {
 const next = new Map(m);
 next.delete(segmentIdx);
 return next;
 });
}

export function updateJobMemoText(memoId: number, memoText: string): void {
 jobMemos.update((m) => {
 const next = new Map(m);
 for (const [idx, memo] of next) {
 if (memo.id === memoId) {
 next.set(idx, { ...memo, memo_text: memoText });
 break;
 }
 }
 return next;
 });
}
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
git add frontend/src/lib/stores/jobMemos.ts
git commit -m "$(cat <<'EOF'
feat(memo): add jobMemos store for per-job segment→memo mapping

Map<segmentIdx, JobMemoLiteDto>로 O(1) 조회. ReadyScreen 마운트 시
loadJobMemos(jobId) 한 번 호출, SegmentMemo 컴포넌트들이 이 map으로
자신의 저장 상태를 판단.

낙관적 업데이트 헬퍼: setJobMemo / unsetJobMemo / updateJobMemoText.
EOF
)"
```

---

### Task 4.2: `SegmentMemo.svelte` 컴포넌트

**Files:**
- Create: `frontend/src/lib/ui/SegmentMemo.svelte`

📎 버튼 + 저장됐을 때 메모 입력 영역. 409 충돌 시 확인 다이얼로그 → 강제 삭제.

- [ ] **Step 1: 기존 아이콘 사용 패턴 확인**

```bash
grep -n "lucide-svelte" frontend/src/lib/ui/SegmentList.svelte
```

- [ ] **Step 2: 컴포넌트 작성**

Write `frontend/src/lib/ui/SegmentMemo.svelte`:

```svelte
<script lang="ts">
 import { Bookmark, Pencil, Trash2 } from 'lucide-svelte';

 import { ApiError } from '$lib/api/client';
 import { memoApi } from '$lib/api/memo';
 import {
 jobMemos,
 setJobMemo,
 unsetJobMemo,
 updateJobMemoText,
 } from '$lib/stores/jobMemos';
 import { refreshMemos } from '$lib/stores/memos';

 export let jobId: string;
 export let segmentIdx: number;

 let editing = false;
 let editValue = '';
 let saving = false;

 $: memo = $jobMemos.get(segmentIdx);
 $: isSaved = memo !== undefined;

 async function toggleSave() {
 if (saving) return;
 saving = true;
 try {
 const res = await memoApi.toggleSave(jobId, segmentIdx);
 if (res.action === 'created' && res.memo) {
 setJobMemo({
 id: res.memo.id,
 job_id: res.memo.job_id,
 segment_idx: res.memo.segment_idx,
 memo_text: res.memo.memo_text,
 });
 refreshMemos(); // 전역 리스트 갱신 (불변 관계)
 } else if (res.action === 'deleted') {
 unsetJobMemo(segmentIdx);
 refreshMemos();
 }
 } catch (err) {
 if (err instanceof ApiError && err.status === 409) {
 const detail = (err as ApiError & { detail?: unknown }).detail;
 const memoId =
 typeof detail === 'object' && detail && 'memo_id' in detail
 ? (detail as { memo_id: number }).memo_id
 : memo?.id;
 if (memoId && confirm('이 메모에 내용이 있어요. 함께 삭제할까요?')) {
 await memoApi.delete(memoId);
 unsetJobMemo(segmentIdx);
 refreshMemos();
 }
 } else {
 console.error('toggle memo failed', err);
 }
 } finally {
 saving = false;
 }
 }

 function startEdit() {
 if (!memo) return;
 editValue = memo.memo_text;
 editing = true;
 }

 async function saveEdit() {
 if (!memo) return;
 const trimmed = editValue.slice(0, 500);
 if (trimmed === memo.memo_text) {
 editing = false;
 return;
 }
 try {
 await memoApi.updateText(memo.id, trimmed);
 updateJobMemoText(memo.id, trimmed);
 refreshMemos();
 } catch (err) {
 console.error('update memo failed', err);
 } finally {
 editing = false;
 }
 }

 function cancelEdit() {
 editing = false;
 }

 function handleKey(e: KeyboardEvent) {
 if (e.key === 'Enter' && !e.shiftKey) {
 e.preventDefault();
 saveEdit();
 } else if (e.key === 'Escape') {
 cancelEdit();
 }
 }
</script>

<div class="flex items-start gap-2">
 <button
 type="button"
 on:click|stopPropagation={toggleSave}
 disabled={saving}
 class="shrink-0 p-1 rounded transition-colors
 {isSaved
 ? 'text-brand'
 : 'text-text-secondary-light dark:text-text-secondary-dark hover:text-brand'}
 disabled:opacity-50"
 aria-label={isSaved ? '저장 해제' : '저장'}
 title={isSaved ? '저장 해제' : '저장'}
 >
 <Bookmark size={16} fill={isSaved ? 'currentColor' : 'none'} strokeWidth={1.75} />
 </button>

 {#if isSaved && memo}
 <div class="flex-1 min-w-0">
 {#if editing}
 <!-- svelte-ignore a11y-autofocus -->
 <textarea
 autofocus
 bind:value={editValue}
 on:keydown={handleKey}
 on:blur={saveEdit}
 maxlength={500}
 rows="2"
 class="w-full text-[12px] p-2 rounded-md border
 border-divider-light dark:border-white/10
 bg-surface-light dark:bg-surface-dark
 text-text-primary-light dark:text-text-primary-dark
 focus:outline-none focus:ring-1 focus:ring-brand resize-none"
 placeholder="메모 (최대 500자, Enter 저장, Esc 취소)"
 />
 {:else}
 <button
 type="button"
 on:click|stopPropagation={startEdit}
 class="w-full text-left text-[12px] leading-snug
 text-text-secondary-light dark:text-text-secondary-dark
 hover:text-text-primary-light dark:hover:text-text-primary-dark
 transition-colors"
 >
 {#if memo.memo_text}
 <span class="whitespace-pre-wrap">💭 {memo.memo_text}</span>
 <span class="text-[10px] opacity-60 ml-1">
 <Pencil size={10} class="inline" />
 </span>
 {:else}
 <span class="opacity-60">＋ 메모 추가</span>
 {/if}
 </button>
 {/if}
 </div>
 {/if}
</div>
```

- [ ] **Step 3: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -10
```

Expected: 0 errors.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/SegmentMemo.svelte
git commit -m "$(cat <<'EOF'
feat(memo): add SegmentMemo component (📎 toggle + inline memo edit)

- 📎 클릭: toggleSave API 호출, 낙관적 업데이트 + 전역 리스트 refresh
- 409 시 confirm 다이얼로그 → 명시적 DELETE (스펙 §4.2)
- 저장된 상태에서 메모 영역 표시. 클릭하면 textarea 로 전환.
- Enter 저장, Esc 취소, blur 저장. maxlength 500.

jobMemos map으로 저장 상태 O(1) 조회.
EOF
)"
```

---

### Task 4.3: SegmentList에 SegmentMemo 삽입

**Files:**
- Modify: `frontend/src/lib/ui/SegmentList.svelte`
- Modify: `frontend/src/lib/screens/ReadyScreen.svelte` (jobMemos load)

- [ ] **Step 1: SegmentList 현재 구조 확인**

```bash
head -50 frontend/src/lib/ui/SegmentList.svelte
wc -l frontend/src/lib/ui/SegmentList.svelte
```

300줄을 넘으면 분리 대상이지만, 이번엔 SegmentMemo 삽입만. 기존 각 세그먼트 렌더링 블록(카드/텍스트 영역) 에 SegmentMemo 추가.

- [ ] **Step 2: SegmentList import + 배치**

Edit `frontend/src/lib/ui/SegmentList.svelte`:

1. `<script>` 상단 import 추가:
 ```ts
 import SegmentMemo from '$lib/ui/SegmentMemo.svelte';
 ```

2. 각 세그먼트 렌더링 영역(텍스트 아래 또는 옆) 에 SegmentMemo 배치. 기존 스크립트 맨 위 export 중 `jobId` 가 있는지 확인 — 있으면 재사용, 없으면 새로 prop 추가:
 ```svelte
 <script lang="ts">
 // 기존 props ...
 export let jobId: string;
 </script>
 ```

3. 각 segment 블록 내 텍스트 바로 아래 (또는 카드 우상단)에 삽입:
 ```svelte
 <!-- 세그먼트 카드 예시 구조 (기존에 맞춰 삽입 위치 조정) -->
 <div class="segment-card ...">
 <div class="flex items-start gap-2">
 <div class="flex-1">
 <div class="timestamp">...</div>
 <div class="text">{segment.text}</div>
 </div>
 <SegmentMemo {jobId} segmentIdx={segment.idx} />
 </div>
 </div>
 ```

 실제 SegmentList의 구조가 다르면 유사 위치에 맞춰 조정. 핵심은:
 - `jobId` 를 SegmentList 레벨에서 받아 모든 자식 SegmentMemo로 전달
 - `segmentIdx` 는 각 segment의 `idx` 를 쓴다

- [ ] **Step 3: ReadyScreen에서 jobMemos 로드**

Edit `frontend/src/lib/screens/ReadyScreen.svelte`:

1. 상단 import 추가:
 ```ts
 import { loadJobMemos, clearJobMemos } from '$lib/stores/jobMemos';
 ```

2. 기존 `onMount` 내 job/segments 로드 후 호출:
 ```ts
 onMount(async () => {
 try {
 [job, segments] = await Promise.all([api.getJob(jobId), api.segments(jobId)]);
 loadJobMemos(jobId); // ← 추가
 } catch (e) {
 // ... 기존 404 처리 ...
 }
 });
 ```

3. `onDestroy` (또는 별도 추가) 에 cleanup:
 ```ts
 onDestroy(() => {
 unshort?.();
 clearJobMemos(); // ← 추가
 });
 ```

4. SegmentList에 `jobId` prop 전달:
 ```svelte
 <SegmentList
 {jobId} <!-- ← 추가 -->
 {segments}
 bind:currentTime
 onJump={(t) => playerRef?.seekTo(t)}
 language={job?.language}
 />
 ```

- [ ] **Step 4: 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -10
```

Expected: 0 errors. 만약 SegmentList가 이미 jobId를 받고 있었다면 중복 prop 에러 — 기존 prop 재사용.

- [ ] **Step 5: 프론트 빌드**

```bash
npm run build 2>&1 | tail -5
```

Expected: 빌드 성공.

- [ ] **Step 6: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/SegmentList.svelte frontend/src/lib/screens/ReadyScreen.svelte
git commit -m "$(cat <<'EOF'
feat(memo): integrate SegmentMemo into SegmentList + load jobMemos

- SegmentList에 jobId prop 추가, 각 세그먼트에 <SegmentMemo> 삽입
- ReadyScreen: onMount에서 loadJobMemos(jobId), onDestroy에서 clearJobMemos

SegmentMemo는 jobMemos store로 자신의 저장 상태를 O(1) 판단.
EOF
)"
```

---

### Phase 4 완료 검증 (프론트만)

- [ ] **Step 1: 빌드 + 타입체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

Expected: 0 errors, 빌드 성공.

- [ ] **Step 2: 커밋 현황**

```bash
cd /Users/loki/GenSub
git log --oneline feature/memo ^master | cat
```

Expected: 14개 커밋 (Phase 1·2·3 11개 + Phase 4 3개).

Phase 4 완료. **현재 상태는 "영상 열면 각 세그먼트에 📎 버튼이 보이고 저장·메모 수정 가능"** 인 상태. 전역 리스트/사이드바 탭은 Phase 5.
