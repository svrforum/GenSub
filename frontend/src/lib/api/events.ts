import type { JobProgressEvent } from './types';

export interface EventHandlers {
  onProgress?: (event: JobProgressEvent) => void;
  onDone?: (status: string) => void;
  onError?: (message: string) => void;
}

export function subscribeJobEvents(jobId: string, handlers: EventHandlers): () => void {
  const es = new EventSource(`/api/jobs/${jobId}/events`);

  es.addEventListener('progress', (evt) => {
    try {
      const data = JSON.parse((evt as MessageEvent).data) as JobProgressEvent;
      handlers.onProgress?.(data);
    } catch {
      /* ignore malformed */
    }
  });

  es.addEventListener('done', (evt) => {
    try {
      const data = JSON.parse((evt as MessageEvent).data) as { status: string };
      handlers.onDone?.(data.status);
    } catch {
      handlers.onDone?.('ready');
    }
    es.close();
  });

  es.addEventListener('error', (evt) => {
    if ((evt as MessageEvent).data) {
      try {
        const data = JSON.parse((evt as MessageEvent).data) as { message: string };
        handlers.onError?.(data.message);
      } catch {
        handlers.onError?.('unknown error');
      }
      es.close();
    }
  });

  return () => es.close();
}
