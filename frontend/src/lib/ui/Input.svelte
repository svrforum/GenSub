<script lang="ts">
  export let value = '';
  export let placeholder = '';
  export let type: 'text' | 'url' = 'text';
  export let disabled = false;
  export let id: string | undefined = undefined;
  export let autofocus = false;
</script>

{#if type === 'url'}
  <!-- svelte-ignore a11y-autofocus -->
  <input
    {id}
    type="url"
    {placeholder}
    {disabled}
    bind:value
    on:input
    on:change
    on:keydown
    {autofocus}
    class="w-full bg-transparent border-0 border-b-2 border-divider-light dark:border-divider-dark
           py-4 text-display text-text-primary-light dark:text-text-primary-dark
           placeholder:text-text-secondary-light dark:placeholder:text-text-secondary-dark
           focus:border-brand focus:outline-none transition-colors"
  />
{:else}
  <!-- svelte-ignore a11y-autofocus -->
  <input
    {id}
    type="text"
    {placeholder}
    {disabled}
    bind:value
    on:input
    on:change
    on:keydown
    {autofocus}
    class="w-full bg-transparent border-0 border-b-2 border-divider-light dark:border-divider-dark
           py-4 text-display text-text-primary-light dark:text-text-primary-dark
           placeholder:text-text-secondary-light dark:placeholder:text-text-secondary-dark
           focus:border-brand focus:outline-none transition-colors"
  />
{/if}
