from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine

from app.models.job import Job, JobStatus


def test_job_creation_and_persistence():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        job = Job(
            id="abc123",
            source_url="https://youtube.com/watch?v=xyz",
            source_kind="url",
            model_name="small",
            status=JobStatus.pending,
            progress=0.0,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        session.add(job)
        session.commit()

    with Session(engine) as session:
        fetched = session.get(Job, "abc123")
        assert fetched is not None
        assert fetched.status == JobStatus.pending
        assert fetched.source_kind == "url"
        assert fetched.cancel_requested is False


def test_job_status_values():
    assert JobStatus.pending.value == "pending"
    assert JobStatus.downloading.value == "downloading"
    assert JobStatus.transcribing.value == "transcribing"
    assert JobStatus.ready.value == "ready"
    assert JobStatus.burning.value == "burning"
    assert JobStatus.done.value == "done"
    assert JobStatus.failed.value == "failed"
