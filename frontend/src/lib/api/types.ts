export type JobStatus =
  | 'pending'
  | 'downloading'
  | 'transcribing'
  | 'ready'
  | 'burning'
  | 'done'
  | 'failed';

export type ModelName = 'tiny' | 'base' | 'small' | 'medium' | 'large-v3';

export interface JobDto {
  id: string;
  source_url: string | null;
  source_kind: 'url' | 'upload';
  title: string | null;
  duration_sec: number | null;
  language: string | null;
  model_name: string;
  status: JobStatus;
  progress: number;
  stage_message: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  expires_at: string;
  cancel_requested: boolean;
  pinned?: boolean;
}

export interface SegmentDto {
  idx: number;
  start: number;
  end: number;
  text: string;
  avg_logprob: number | null;
  no_speech_prob: number | null;
  edited: boolean;
}

export interface ConfigDto {
  default_model: ModelName;
  available_models: ModelName[];
  max_video_minutes: number;
  max_upload_mb: number;
  job_ttl_hours: number;
}

export interface JobCreateRequest {
  url?: string;
  model: ModelName;
  language?: string;
  initial_prompt?: string;
}

export interface JobProgressEvent {
  status: JobStatus;
  progress: number;
  stage_message: string | null;
  active_count?: number;
  ahead_count?: number;
}

// 메모 기능 (2026-04-22 spec)
export interface MemoDto {
  id: number;
  job_id: string;
  segment_idx: number;
  memo_text: string;
  segment_text_snapshot: string;
  segment_start: number;
  segment_end: number;
  job_title_snapshot: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoListItemDto {
  id: number;
  job_id: string;
  segment_idx: number;
  memo_text: string;
  segment_text: string;
  start: number;
  end: number;
  job_title: string | null;
  job_alive: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobMemoLiteDto {
  id: number;
  job_id: string;
  segment_idx: number;
  memo_text: string;
}

// 검색 기능 (2026-04-28 spec)
export type SearchKind = 'job' | 'memo' | 'segment';

export interface SearchHit {
  kind: SearchKind;
  job_id: string;
  job_title: string | null;
  // kind === 'segment' 또는 'memo' 일 때 채워짐
  segment_idx?: number;
  segment_text?: string;
  start?: number;
  end?: number;
  // kind === 'memo' 일 때만
  memo_id?: number;
  memo_text?: string;
}
