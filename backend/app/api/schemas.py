from typing import Literal

from pydantic import BaseModel, Field

ModelName = Literal["tiny", "base", "small", "medium", "large-v3"]


class JobCreateRequest(BaseModel):
    url: str | None = None
    model: ModelName = "small"
    language: str | None = None
    initial_prompt: str | None = None


class JobResponse(BaseModel):
    id: str
    source_url: str | None
    source_kind: str
    title: str | None
    duration_sec: float | None
    language: str | None
    model_name: str
    status: str
    progress: float
    stage_message: str | None
    error_message: str | None
    created_at: str
    updated_at: str
    expires_at: str
    cancel_requested: bool


class SegmentResponse(BaseModel):
    idx: int
    start: float
    end: float
    text: str
    avg_logprob: float | None
    no_speech_prob: float | None
    edited: bool


class SegmentPatchRequest(BaseModel):
    text: str | None = None
    start: float | None = Field(default=None, ge=0.0)
    end: float | None = Field(default=None, ge=0.0)


class SearchReplaceRequest(BaseModel):
    find: str
    replace: str
    case_sensitive: bool = False


class SearchReplaceResponse(BaseModel):
    changed_count: int
