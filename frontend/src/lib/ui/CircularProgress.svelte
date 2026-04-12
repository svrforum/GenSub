<script lang="ts">
  import { tweened } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';

  export let value = 0; // 0.0 ~ 1.0
  export let size = 140;
  export let stroke = 8;

  const tweenedValue = tweened(value, { duration: 400, easing: cubicOut });
  $: tweenedValue.set(Math.max(0, Math.min(1, value)));

  $: radius = (size - stroke) / 2;
  $: circumference = 2 * Math.PI * radius;
  $: offset = circumference * (1 - $tweenedValue);
  $: percentText = Math.round($tweenedValue * 100);
</script>

<div class="relative flex items-center justify-center" style="width:{size}px; height:{size}px">
  <svg width={size} height={size} class="-rotate-90">
    <circle
      cx={size / 2}
      cy={size / 2}
      r={radius}
      fill="none"
      class="stroke-divider-light dark:stroke-surface-dark-elevated"
      stroke-width={stroke}
    />
    <circle
      cx={size / 2}
      cy={size / 2}
      r={radius}
      fill="none"
      class="stroke-brand dark:stroke-brand-dark"
      stroke-width={stroke}
      stroke-linecap="round"
      stroke-dasharray={circumference}
      stroke-dashoffset={offset}
      style="transition: stroke-dashoffset 400ms cubic-bezier(0.2, 0.9, 0.2, 1.05)"
    />
  </svg>
  <div class="absolute text-display font-bold">
    {percentText}
    <span class="text-title text-text-secondary-light dark:text-text-secondary-dark">%</span>
  </div>
</div>
