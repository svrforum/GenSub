<script lang="ts">
  type Option = { value: string; label: string };
  export let options: Option[] = [];
  export let value: string;
</script>

<div
  class="inline-flex items-center p-1 rounded-xl bg-divider-light dark:bg-surface-dark-elevated gap-1"
  role="tablist"
>
  {#each options as opt}
    <button
      type="button"
      role="tab"
      aria-selected={value === opt.value}
      on:click={() => (value = opt.value)}
      class="px-4 py-2 text-caption font-semibold rounded-lg transition-all ease-spring
             {value === opt.value
               ? 'bg-surface-light dark:bg-surface-dark text-text-primary-light dark:text-text-primary-dark shadow-sm'
               : 'text-text-secondary-light dark:text-text-secondary-dark'}"
    >
      {opt.label}
    </button>
  {/each}
</div>
