<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';

  export let open = false;
  export let onClose: () => void = () => {};
</script>

{#if open}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
    on:click={onClose}
    transition:fade={{ duration: 200 }}
  />
  <div
    class="fixed inset-x-0 bottom-0 z-50 bg-surface-light dark:bg-surface-dark
           rounded-t-[28px] shadow-card pb-6"
    transition:fly={{ y: 400, duration: 380, easing: cubicOut }}
  >
    <div class="flex justify-center pt-3 pb-1">
      <div class="w-10 h-1.5 rounded-full bg-divider-light dark:bg-divider-dark" />
    </div>
    <div class="px-6 pt-2">
      <slot />
    </div>
  </div>
{/if}
