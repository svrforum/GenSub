<script lang="ts">
  import { onMount } from 'svelte';

  export let src: string;
  export let vttSrc: string;
  export let currentTime = 0;
  export let onError: (() => void) | undefined = undefined;
  export let onLoadedMetadata: (() => void) | null = null;

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

  // video 클릭 시 포커스를 되돌림
  function handleClick() {
    setTimeout(() => {
      if (document.activeElement === videoEl) {
        (document.activeElement as HTMLElement).blur();
      }
    }, 0);
  }

  // source 로드 실패 감지: networkState로 판단
  onMount(() => {
    if (!videoEl) return;
    const checkError = () => {
      // networkState 3 = NETWORK_NO_SOURCE
      if (videoEl.networkState === 3 || videoEl.error) {
        onError?.();
      }
    };
    videoEl.addEventListener('error', checkError);
    // source 에러는 video로 안 올라오므로 loadeddata 실패 시 타임아웃으로 감지
    const timer = setTimeout(() => {
      if (videoEl && videoEl.readyState === 0 && videoEl.networkState !== 2) {
        onError?.();
      }
    }, 5000);
    return () => {
      videoEl?.removeEventListener('error', checkError);
      clearTimeout(timer);
    };
  });
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="w-full h-full" on:click={handleClick}>
  <video
    bind:this={videoEl}
    on:timeupdate={onTimeUpdate}
    on:loadedmetadata={() => onLoadedMetadata?.()}
    class="w-full h-full bg-black"
    controls
    preload="metadata"
    crossorigin="anonymous"
  >
    <source {src} />
    <track default kind="subtitles" srclang="und" label="자막" src={vttSrc} />
  </video>
</div>
