"""Memo CRUD 서비스. Session 생명주기를 소유한다."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models.job import Job
from app.models.memo import Memo
from app.models.segment import Segment


@dataclass
class ToggleResult:
    action: Literal["created", "deleted", "conflict"]
    memo: Memo | None


def toggle_save_memo(engine: Engine, job_id: str, segment_idx: int) -> ToggleResult:
    """스펙 §4.2 POST 토글 로직.

    - 메모 없음 → 생성 (memo_text=""), Job auto-pin
    - 메모 있음 + memo_text 빈 문자열 → 삭제
    - 메모 있음 + memo_text 내용 있음 → conflict

    Raises:
        LookupError: Job 또는 Segment가 존재하지 않음.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job is None:
            raise LookupError(f"job not found: {job_id}")

        seg_stmt = select(Segment).where(
            Segment.job_id == job_id, Segment.idx == segment_idx
        )
        seg_result = session.exec(seg_stmt)
        segment = seg_result.first()
        if segment is None:
            raise LookupError(f"segment not found: {job_id}/{segment_idx}")

        memo_stmt = select(Memo).where(
            Memo.job_id == job_id, Memo.segment_idx == segment_idx
        )
        memo_result = session.exec(memo_stmt)
        existing = memo_result.first()

        if existing is not None:
            if existing.memo_text == "":
                session.delete(existing)
                session.commit()
                return ToggleResult(action="deleted", memo=None)
            return ToggleResult(action="conflict", memo=existing)

        memo = Memo(
            job_id=job_id,
            segment_idx=segment_idx,
            memo_text="",
            segment_text_snapshot=segment.text,
            segment_start=segment.start,
            segment_end=segment.end,
            job_title_snapshot=job.title,
        )
        session.add(memo)

        if not job.pinned:
            job.pinned = True
            job.updated_at = datetime.now(UTC)
            session.add(job)

        session.commit()
        session.refresh(memo)
        return ToggleResult(action="created", memo=memo)


def get_memo_by_segment(engine: Engine, job_id: str, segment_idx: int) -> Memo | None:
    with Session(engine) as session:
        stmt = select(Memo).where(
            Memo.job_id == job_id, Memo.segment_idx == segment_idx
        )
        result = session.exec(stmt)
        return result.first()


def list_memos_for_job(engine: Engine, job_id: str) -> list[Memo]:
    with Session(engine) as session:
        stmt = (
            select(Memo)
            .where(Memo.job_id == job_id)
            .order_by(Memo.segment_idx)
        )
        result = session.exec(stmt)
        return list(result.all())


def update_memo_text(engine: Engine, memo_id: int, memo_text: str) -> Memo | None:
    with Session(engine) as session:
        memo = session.get(Memo, memo_id)
        if memo is None:
            return None
        memo.memo_text = memo_text
        memo.updated_at = datetime.now(UTC)
        session.add(memo)
        session.commit()
        session.refresh(memo)
        return memo


def delete_memo(engine: Engine, memo_id: int) -> bool:
    with Session(engine) as session:
        memo = session.get(Memo, memo_id)
        if memo is None:
            return False
        session.delete(memo)
        session.commit()
        return True


def delete_memos_for_job(engine: Engine, job_id: str) -> int:
    """Job 삭제와 함께 호출. 제거된 메모 개수 반환."""
    with Session(engine) as session:
        stmt = select(Memo).where(Memo.job_id == job_id)
        result = session.exec(stmt)
        memos = list(result.all())
        for m in memos:
            session.delete(m)
        session.commit()
        return len(memos)
