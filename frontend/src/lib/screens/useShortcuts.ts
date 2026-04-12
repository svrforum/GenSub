export interface ShortcutHandlers {
  togglePlay: () => void;
  prevSegment: () => void;
  nextSegment: () => void;
  seekRelative: (delta: number) => void;
  regenerateCurrent: () => void;
  toggleSearch: () => void;
}

export function installShortcuts(handlers: ShortcutHandlers): () => void {
  function onKey(e: KeyboardEvent) {
    const target = e.target as HTMLElement | null;
    if (target && (target.tagName === 'INPUT' || target.isContentEditable)) {
      return;
    }
    switch (e.key) {
      case ' ':
        e.preventDefault();
        handlers.togglePlay();
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
        handlers.seekRelative(-5);
        break;
      case 'l':
        handlers.seekRelative(5);
        break;
      case 'r':
      case 'R':
        handlers.regenerateCurrent();
        break;
      default:
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') {
          e.preventDefault();
          handlers.toggleSearch();
        }
    }
  }
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}
