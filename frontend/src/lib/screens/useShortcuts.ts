export interface ShortcutHandlers {
  togglePlay: () => void;
  prevSegment: () => void;
  nextSegment: () => void;
  seekRelative: (delta: number) => void;
  toggleSearch: () => void;
}

export function installShortcuts(handlers: ShortcutHandlers): () => void {
  function onKey(e: KeyboardEvent) {
    const target = e.target as HTMLElement | null;
    // INPUT, contentEditable, TEXTAREA에서는 단축키 무시
    if (
      target &&
      (target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable)
    ) {
      return;
    }
    switch (e.key) {
      case ' ':
        e.preventDefault();
        handlers.togglePlay();
        break;
      case 'ArrowLeft':
        e.preventDefault();
        handlers.seekRelative(-5);
        break;
      case 'ArrowRight':
        e.preventDefault();
        handlers.seekRelative(5);
        break;
      case 'ArrowUp':
        e.preventDefault();
        handlers.prevSegment();
        break;
      case 'ArrowDown':
        e.preventDefault();
        handlers.nextSegment();
        break;
      case 'j':
        handlers.seekRelative(-10);
        break;
      case 'l':
        handlers.seekRelative(10);
        break;
      default:
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') {
          e.preventDefault();
          handlers.toggleSearch();
        }
    }
  }
  // capture: true로 브라우저 기본 동작보다 먼저 처리
  window.addEventListener('keydown', onKey, true);
  return () => window.removeEventListener('keydown', onKey, true);
}
