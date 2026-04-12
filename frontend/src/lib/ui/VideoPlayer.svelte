<script lang="ts">
  export let src: string;
  export let vttSrc: string;
  export let currentTime = 0;

  let videoEl: HTMLVideoElement;

  export function seekTo(t: number) {
    if (videoEl) {
      videoEl.currentTime = t;
      videoEl.play().catch(() => {});
    }
  }

  export function togglePlay() {
    if (!videoEl) return;
    if (videoEl.paused) videoEl.play();
    else videoEl.pause();
  }

  function onTimeUpdate() {
    currentTime = videoEl?.currentTime ?? 0;
  }
</script>

<video
  bind:this={videoEl}
  on:timeupdate={onTimeUpdate}
  class="w-full h-full bg-black"
  controls
  preload="metadata"
  crossorigin="anonymous"
>
  <source {src} />
  <track default kind="subtitles" srclang="und" label="자막" src={vttSrc} />
</video>
