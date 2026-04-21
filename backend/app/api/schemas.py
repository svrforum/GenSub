from typing import Literal

from pydantic import BaseModel, Field, field_validator

ModelName = Literal["tiny", "base", "small", "medium", "large-v3"]


class JobCreateRequest(BaseModel):
    url: str | None = None
    model: ModelName = "small"
    language: str | None = None
    initial_prompt: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


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


class MemoPatchRequest(BaseModel):
    memo_text: str = Field(min_length=0, max_length=500)
