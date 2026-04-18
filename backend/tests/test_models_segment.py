from datetime import UTC, datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine, select

from app.models.job import Job, JobStatus
from app.models.segment import Segment


def test_segment_belongs_to_job():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        job = Job(
            id="j1",
            source_kind="upload",
            model_name="small",
            status=JobStatus.ready,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        s.add(job)
        s.add(Segment(job_id="j1", idx=0, start=0.0, end=3.5, text="안녕하세요", avg_logprob=-0.2))
        s.add(Segment(job_id="j1", idx=1, start=3.5, end=7.0, text="반갑습니다", avg_logprob=-0.1))
        s.commit()

        rows = s.exec(
            select(Segment).where(Segment.job_id == "j1").order_by(Segment.idx)
        ).all()
        assert len(rows) == 2
        assert rows[0].text == "안녕하세요"
        assert rows[1].start == 3.5
        assert rows[0].edited is False
