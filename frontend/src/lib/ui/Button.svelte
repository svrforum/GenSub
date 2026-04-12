<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'ghost' = 'primary';
  export let disabled = false;
  export let type: 'button' | 'submit' = 'button';
  export let fullWidth = false;

  const variantClass: Record<string, string> = {
    primary:
      'bg-brand text-white hover:bg-brand-pressed dark:bg-brand-dark dark:hover:bg-brand',
    secondary:
      'bg-surface-light text-text-primary-light dark:bg-surface-dark dark:text-text-primary-dark border border-divider-light dark:border-divider-dark',
    ghost:
      'bg-transparent text-text-secondary-light hover:text-text-primary-light dark:text-text-secondary-dark dark:hover:text-text-primary-dark'
  };
</script>

<button
  {type}
  {disabled}
  on:click
  class="inline-flex items-center justify-center h-14 px-6 rounded-button font-semibold text-body
         transition-all ease-spring active:scale-[0.97]
         disabled:opacity-50 disabled:cursor-not-allowed
         {variantClass[variant]}
         {fullWidth ? 'w-full' : ''}"
>
  <slot />
</button>
