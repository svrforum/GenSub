from sqlmodel import Field, SQLModel


class Segment(SQLModel, table=True):
    __tablename__ = "segment"

    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    idx: int
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    edited: bool = False
    words: str | None = None
