<script lang="ts">
  export let src: string;
  export let vttSrc: string;
  export let currentTime = 0;
  export let onError: (() => void) | undefined = undefined;

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

  function handleError() {
    onError?.();
  }

  // video 클릭 시 포커스가 video로 가면 단축키가 안 먹으므로
  // 클릭 후 포커스를 body로 되돌림
  function handleClick() {
    setTimeout(() => {
      if (document.activeElement === videoEl) {
        (document.activeElement as HTMLElement).blur();
      }
    }, 0);
  }
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="w-full h-full" on:click={handleClick}>
  <video
    bind:this={videoEl}
    on:timeupdate={onTimeUpdate}
    on:error={handleError}
    class="w-full h-full bg-black"
    controls
    preload="metadata"
    crossorigin="anonymous"
  >
    <source {src} />
    <track default kind="subtitles" srclang="und" label="자막" src={vttSrc} />
  </video>
</div>
