<script lang="ts">
  import { Bookmark, Pencil } from 'lucide-svelte';

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
            <span class="text-[10px] opacity-60 ml-1 inline-flex align-middle">
              <Pencil size={10} />
            </span>
          {:else}
            <span class="opacity-60">＋ 메모 추가</span>
          {/if}
        </button>
      {/if}
    </div>
  {/if}
</div>
