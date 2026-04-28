"""검색 서비스. 자막·메모·영상 제목을 LIKE 부분 매치로 검색."""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models.job import Job
from app.models.memo import Memo
from app.models.segment import Segment


@dataclass
class SearchHit:
    kind: Literal["job", "memo", "segment"]
    job_id: str
    job_title: str | None
    segment_idx: int | None = None
    segment_text: str | None = None
    start: float | None = None
    end: float | None = None
    memo_id: int | None = None
    memo_text: str | None = None


def search_all(engine: Engine, query: str, limit: int = 50) -> list[SearchHit]:
    """자막 + 메모 + 영상 제목을 query로 부분 매치 검색.

    - 빈 query → 즉시 빈 리스트.
    - 결과 순서: job → memo → segment.
    - 각 그룹 내: pinned(북마크) 영상 우선, 그 다음 updated_at desc.
    - INNER JOIN 으로 orphan segment/memo 자동 제외.
    - SQLite ilike 는 ASCII 에서 case-insensitive (한국어는 본래 case 없음).
    """
    q = (query or "").strip()
    if not q:
        return []

    pattern = f"%{q}%"
    hits: list[SearchHit] = []

    with Session(engine) as session:
        # 1) Job titles — pinned first
        job_stmt = (
            select(Job)
            .where(Job.title.ilike(pattern))  # type: ignore[union-attr]
            .order_by(Job.pinned.desc(), Job.updated_at.desc())  # type: ignore[union-attr]
            .limit(limit)
        )
        job_result = session.exec(job_stmt)
        for job in job_result.all():
            hits.append(SearchHit(
                kind="job",
                job_id=job.id,
                job_title=job.title,
            ))

        # 2) Memos — pinned job's memos first
        memo_stmt = (
            select(Memo, Job)
            .join(Job, Job.id == Memo.job_id)
            .where(
                (Memo.memo_text.ilike(pattern))  # type: ignore[union-attr]
                | (Memo.segment_text_snapshot.ilike(pattern))  # type: ignore[union-attr]
            )
            .order_by(Job.pinned.desc(), Memo.updated_at.desc())  # type: ignore[union-attr]
            .limit(limit)
        )
        memo_result = session.exec(memo_stmt)
        for memo, job in memo_result.all():
            hits.append(SearchHit(
                kind="memo",
                job_id=memo.job_id,
                job_title=job.title,
                memo_id=memo.id,
                memo_text=memo.memo_text,
                segment_idx=memo.segment_idx,
                segment_text=memo.segment_text_snapshot,
                start=memo.segment_start,
                end=memo.segment_end,
            ))

        # 3) Segments — pinned job's segments first
        seg_stmt = (
            select(Segment, Job)
            .join(Job, Job.id == Segment.job_id)
            .where(Segment.text.ilike(pattern))  # type: ignore[union-attr]
            .order_by(Job.pinned.desc(), Job.updated_at.desc(), Segment.idx)  # type: ignore[union-attr]
            .limit(limit)
        )
        seg_result = session.exec(seg_stmt)
        for seg, job in seg_result.all():
            hits.append(SearchHit(
                kind="segment",
                job_id=seg.job_id,
                job_title=job.title,
                segment_idx=seg.idx,
                segment_text=seg.text,
                start=seg.start,
                end=seg.end,
            ))

    return hits[:limit]
