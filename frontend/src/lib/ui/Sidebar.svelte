<script lang="ts">
  import { onMount } from 'svelte';
  import { Bookmark, PenLine, PanelLeftClose, Trash2, Video } from 'lucide-svelte';

  import { api, ApiError } from '$lib/api/jobs';
  import { memoApi } from '$lib/api/memo';
  import type { MemoListItemDto } from '$lib/api/types';
  import { current, openMemo, reset } from '$lib/stores/current';
  import {
    history,
    pushHistory,
    removeFromHistory,
    renameHistory,
    toggleBookmark,
    type HistoryItem
  } from '$lib/stores/history';
  import { memos, refreshMemos, removeMemoLocal } from '$lib/stores/memos';
  import MemoCard from '$lib/ui/MemoCard.svelte';

  export let collapsed = false;
  export let onToggle: () => void = () => {};

  let sidebarTab: 'videos' | 'memos' = 'videos';

  $: if (sidebarTab === 'memos' && !collapsed) {
    refreshMemos();
  }

  async function handleOpenMemo(m: MemoListItemDto) {
    openMemo(m.job_id, m.start);
  }

  async function handleDeleteMemo(memoId: number) {
    removeMemoLocal(memoId);
    try {
      await memoApi.delete(memoId);
    } catch {
      refreshMemos();
    }
  }

  let editingId: string | null = null;
  let editValue = '';
  let validating = false;
  let validated = false;
  let hoveredId: string | null = null;

  $: if (!collapsed && !validated) {
    syncWithServer();
  }

  /**
   * 서버와 히스토리 동기화. localStorage만 믿지 않고 서버가 source of truth.
   * - 서버에 있는 작업 → 히스토리에 추가/갱신 (title 복구, pinned 동기화)
   * - localStorage 항목 중 서버에 **404로 확인된** 것만 제거 (네트워크 에러는 보존)
   */
  async function syncWithServer() {
    if (validated || validating) return;
    validating = true;
    validated = true;

    // 서버 작업 목록 fetch. 네트워크 실패 시 로컬만으로 진행.
    let serverJobs: Array<{ id: string; title: string | null; pinned?: boolean; created_at: string }> = [];
    let serverReachable = false;
    try {
      const res = await api.listRecentJobs(50);
      serverJobs = res.jobs;
      serverReachable = true;
    } catch {
      // 서버 불통 — 히스토리는 손대지 말고 그대로 유지
      validating = false;
      return;
    }

    // 현재 로컬 히스토리 스냅샷
    let localItems: HistoryItem[] = [];
    const unsub = history.subscribe((h) => { localItems = h; });
    unsub();

    const localById = new Map(localItems.map((i) => [i.jobId, i]));
    const serverIds = new Set(serverJobs.map((j) => j.id));

    // 1. 서버에 있는 작업 → 로컬에 추가/갱신
    for (const job of serverJobs) {
      const local = localById.get(job.id);
      // 사용자가 로컬에서 rename한 경우 title 보존, 아니면 서버 title 채택
      const hasCustomRename = local && local.originalTitle && local.title !== local.originalTitle;
      const title = hasCustomRename ? (local!.title) : (job.title ?? local?.title ?? null);
      const originalTitle = job.title ?? local?.originalTitle ?? local?.title ?? null;
      pushHistory({
        jobId: job.id,
        title,
        originalTitle,
        bookmarked: job.pinned ?? local?.bookmarked ?? false,
        createdAt: job.created_at,
      });
    }

    // 2. 로컬에만 있고 서버엔 없는 항목 — 서버에 개별 확인 (list limit 초과 가능성 대비)
    if (serverReachable) {
      for (const item of localItems) {
        if (serverIds.has(item.jobId)) continue;
        try {
          await api.getJob(item.jobId);
          // 존재하면 유지 (list limit을 초과한 오래된 항목)
        } catch (err) {
          // 404만 제거. 네트워크 에러 등은 보존.
          if (err instanceof ApiError && err.status === 404) {
            removeFromHistory(item.jobId);
          }
        }
      }
    }

    validating = false;
  }

  function openJob(jobId: string) {
    current.set({
      screen: 'ready', jobId, job: null,
      progress: 1, stageMessage: '', errorMessage: null
    });
  }

  function startEdit(item: HistoryItem) {
    editingId = item.jobId;
    // 사용자가 직접 지은 이름이면 표시, 원제목과 같으면 빈값(placeholder로 원제목 보임)
    editValue = item.title !== item.originalTitle ? (item.title || '') : '';
  }

  function saveEdit(item: HistoryItem) {
    const val = editValue.trim();
    if (val && val !== item.title) {
      renameHistory(item.jobId, val);
    }
    editingId = null;
  }

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
    // 현재 보고 있는 작업이면 홈으로
    if ($current.jobId === item.jobId) reset();
    if (memoCount > 0) {
      refreshMemos();  // 전역 메모 리스트에서 제거됨 반영
    }
  }

  async function handleBookmark(item: HistoryItem) {
    toggleBookmark(item.jobId);
    try {
      await api.pinJob(item.jobId);
    } catch {
      // 서버 실패 시 되돌리기
      toggleBookmark(item.jobId);
    }
  }

  function handleEditKey(e: KeyboardEvent, item: HistoryItem) {
    if (e.key === 'Enter') { e.preventDefault(); saveEdit(item); }
    else if (e.key === 'Escape') { editingId = null; }
  }

  // 날짜 그룹
  function groupByDate(items: HistoryItem[]) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);
    const monthAgo = new Date(today.getTime() - 30 * 86400000);
    const groups: Map<string, HistoryItem[]> = new Map();
    for (const item of items) {
      const d = new Date(item.createdAt);
      const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      let label: string;
      if (day >= today) label = '오늘';
      else if (day >= yesterday) label = '어제';
      else if (day >= weekAgo) label = '지난 7일';
      else if (day >= monthAgo) label = '지난 30일';
      else label = `${d.getFullYear()}년 ${d.getMonth() + 1}월`;
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label)!.push(item);
    }
    return [...groups.entries()].map(([label, items]) => ({ label, items }));
  }

  $: activeJobId = $current.jobId;
  $: isProcessing = $current.screen === 'processing';
  $: groups = groupByDate($history);

  onMount(() => {
    refreshMemos();
  });
</script>

<aside
  class="fixed top-0 left-0 bottom-0 z-20 flex flex-col
         bg-[#f7f7f8] dark:bg-[#171717]
         transition-all duration-200
         {collapsed ? 'w-0 overflow-hidden' : 'w-[260px]'}"
>
  <!-- 헤더 -->
  <div class="flex items-center gap-2 px-3 h-14 shrink-0">
    <button
      type="button"
      on:click={reset}
      class="flex-1 flex items-center gap-2 px-3 py-2 rounded-xl
             hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
    >
      <div class="w-6 h-6 rounded-md bg-brand flex items-center justify-center">
        <span class="text-white text-xs font-bold">G</span>
      </div>
      <span class="text-sm font-semibold text-text-primary-light dark:text-text-primary-dark">새 자막</span>
    </button>
    <button
      type="button"
      on:click={onToggle}
      class="p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5
             text-text-secondary-light dark:text-text-secondary-dark transition-colors"
      aria-label="사이드바 접기"
    >
      <PanelLeftClose size={18} />
    </button>
  </div>

  <!-- 탭 헤더 -->
  <div class="flex border-b border-black/5 dark:border-white/5 px-3">
    <button
      type="button"
      class="flex-1 py-2 text-[12px] font-medium flex items-center justify-center gap-1.5 transition-colors
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
      class="flex-1 py-2 text-[12px] font-medium flex items-center justify-center gap-1.5 transition-colors
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

  <!-- 리스트 -->
  {#if sidebarTab === 'videos'}
    <nav class="flex-1 overflow-y-auto px-2 pb-2" aria-label="작업 이력">
      {#if $history.length === 0 && !validating}
        <div class="text-[13px] text-text-secondary-light dark:text-text-secondary-dark px-3 py-6 text-center">
          아직 작업 이력이 없어요
        </div>
      {:else}
        {#each groups as group}
          <div class="mt-5 first:mt-2">
            <h3 class="px-3 pb-2 text-[11px] font-medium
                        text-text-secondary-light dark:text-text-secondary-dark">
              {group.label}
            </h3>
            <ul class="space-y-0.5">
              {#each group.items as item (item.jobId)}
                <li
                  class="relative rounded-lg transition-colors duration-100
                         {activeJobId === item.jobId
                           ? 'bg-black/[0.07] dark:bg-white/[0.07]'
                           : 'hover:bg-black/[0.04] dark:hover:bg-white/[0.04]'}"
                  on:mouseenter={() => (hoveredId = item.jobId)}
                  on:mouseleave={() => (hoveredId = null)}
                >
                  {#if editingId === item.jobId}
                    <!-- svelte-ignore a11y-autofocus -->
                    <input
                      type="text"
                      bind:value={editValue}
                      on:blur={() => saveEdit(item)}
                      on:keydown={(e) => handleEditKey(e, item)}
                      autofocus
                      placeholder={item.originalTitle || item.title || '제목 입력'}
                      class="w-full bg-transparent text-sm outline-none
                             px-3 py-2 rounded-lg ring-1 ring-brand/50"
                    />
                  {:else}
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <div
                      class="flex items-center gap-1.5 px-2 py-2 cursor-pointer"
                      on:click={() => openJob(item.jobId)}
                    >
                      <!-- 북마크 (좌측, 항상 보임) -->
                      <button
                        type="button"
                        class="shrink-0 p-0.5 rounded transition-colors
                               {item.bookmarked
                                 ? 'text-brand'
                                 : 'text-transparent hover:text-text-secondary-light dark:hover:text-text-secondary-dark'}"
                        on:click|stopPropagation={() => handleBookmark(item)}
                        aria-label={item.bookmarked ? '북마크 해제' : '북마크'}
                      >
                        <Bookmark size={13} fill={item.bookmarked ? 'currentColor' : 'none'}
                                  strokeWidth={item.bookmarked ? 2 : 1.5} />
                      </button>
                      <span class="flex-1 truncate text-sm
                                   {activeJobId === item.jobId ? 'font-medium' : ''}
                                   {item.title ? 'text-text-primary-light dark:text-text-primary-dark' : 'text-text-secondary-light dark:text-text-secondary-dark italic'}">
                        {item.title || '제목 없음'}
                      </span>
                    </div>
                    <!-- 호버 액션 (우측: 수정 + 삭제만) -->
                    {#if hoveredId === item.jobId || activeJobId === item.jobId}
                      <div
                        class="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-0.5
                               bg-[#f7f7f8] dark:bg-[#171717] rounded-lg pl-1
                               {hoveredId === item.jobId ? 'opacity-100' : 'opacity-0'}
                               transition-opacity duration-100"
                      >
                        <button
                          type="button"
                          class="p-1.5 rounded-md hover:bg-black/5 dark:hover:bg-white/10
                                 text-text-secondary-light dark:text-text-secondary-dark transition-colors"
                          on:click|stopPropagation={() => startEdit(item)}
                          aria-label="이름 변경"
                        >
                          <PenLine size={14} />
                        </button>
                        <button
                          type="button"
                          class="p-1.5 rounded-md hover:bg-danger/10 hover:text-danger
                                 text-text-secondary-light dark:text-text-secondary-dark transition-colors"
                          on:click|stopPropagation={() => confirmDelete(item)}
                          aria-label="삭제"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    {/if}
                  {/if}
                </li>
              {/each}
            </ul>
          </div>
        {/each}
      {/if}
    </nav>
  {:else}
    <nav class="flex-1 overflow-y-auto px-2 py-2" aria-label="저장한 메모">
      {#if $memos.length === 0}
        <div class="text-[13px] text-text-secondary-light dark:text-text-secondary-dark
                    px-3 py-6 text-center leading-relaxed">
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

  <!-- 백그라운드 작업 상태 -->
  {#if isProcessing}
    <div class="shrink-0 border-t border-black/5 dark:border-white/5 px-3 py-3">
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <div
        class="flex items-center gap-3 px-2 py-2 rounded-lg
               bg-brand/5 cursor-pointer hover:bg-brand/10 transition-colors"
        on:click={() => {
          if ($current.jobId) openJob($current.jobId);
        }}
      >
        <div class="relative w-5 h-5 shrink-0">
          <svg class="w-5 h-5 -rotate-90" viewBox="0 0 20 20">
            <circle cx="10" cy="10" r="8" fill="none" stroke-width="2"
                    class="stroke-brand/20" />
            <circle cx="10" cy="10" r="8" fill="none" stroke-width="2"
                    class="stroke-brand" stroke-linecap="round"
                    stroke-dasharray={50.3}
                    stroke-dashoffset={50.3 * (1 - $current.progress)} />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-[12px] font-medium text-brand truncate">
            {$current.stageMessage || '처리 중...'}
          </div>
          <div class="text-[11px] text-text-secondary-light dark:text-text-secondary-dark">
            {Math.round($current.progress * 100)}%
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- 하단 안내 -->
  <div class="shrink-0 border-t border-black/5 dark:border-white/5 px-3 py-3">
    <div class="text-[12px] leading-relaxed text-text-secondary-light dark:text-text-secondary-dark">
      작업은 <strong class="text-text-primary-light dark:text-text-primary-dark">직접 삭제할 때까지 보관</strong>돼요.
      <br />
      디스크 공간이 부족해지면 정리해 주세요.
    </div>
  </div>
</aside>
