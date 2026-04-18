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
  has_openai_fallback: boolean;
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
