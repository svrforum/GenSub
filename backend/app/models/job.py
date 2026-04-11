from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    pending = "pending"
    downloading = "downloading"
    transcribing = "transcribing"
    ready = "ready"
    burning = "burning"
    done = "done"
    failed = "failed"


class SourceKind(str, Enum):
    url = "url"
    upload = "upload"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(SQLModel, table=True):
    __tablename__ = "job"

    id: str = Field(primary_key=True)
    source_url: str | None = None
    source_kind: str
    title: str | None = None
    duration_sec: float | None = None
    language: str | None = None
    model_name: str
    initial_prompt: str | None = None
    status: JobStatus = JobStatus.pending
    progress: float = 0.0
    stage_message: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime
    cancel_requested: bool = False
