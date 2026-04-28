import { http } from './client';
import type { SearchHit } from './types';

export const searchApi = {
  query: (q: string, limit = 50) => {
    const params = new URLSearchParams({ q, limit: String(limit) });
    return http.get<{ items: SearchHit[] }>(`/api/search?${params.toString()}`);
  },
};
