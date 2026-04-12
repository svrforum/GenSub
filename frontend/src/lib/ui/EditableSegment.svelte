<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let value: string;
  export let editing = false;

  let inputEl: HTMLSpanElement;
  const dispatch = createEventDispatcher<{ save: string; cancel: void }>();

  $: if (editing && inputEl) {
    setTimeout(() => {
      inputEl.focus();
      const range = document.createRange();
      range.selectNodeContents(inputEl);
      const sel = window.getSelection();
      sel?.removeAllRanges();
      sel?.addRange(range);
    }, 0);
  }

  function commit() {
    const text = inputEl?.innerText?.trim() ?? value;
    dispatch('save', text);
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      dispatch('cancel');
    }
  }
</script>

{#if editing}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <span
    bind:this={inputEl}
    contenteditable="true"
    class="outline-none ring-2 ring-brand rounded px-1"
    on:keydown={onKey}
    on:blur={commit}
  >{value}</span>
{:else}
  <span>{value}</span>
{/if}
