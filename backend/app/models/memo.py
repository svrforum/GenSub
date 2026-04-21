from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Memo(SQLModel, table=True):
    __tablename__ = "memo"
    __table_args__ = (
        UniqueConstraint("job_id", "segment_idx", name="uq_memo_job_segment"),
    )

    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(index=True)
    segment_idx: int
    memo_text: str = Field(default="", max_length=500)

    segment_text_snapshot: str
    segment_start: float
    segment_end: float
    job_title_snapshot: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
