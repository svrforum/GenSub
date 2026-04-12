from sqlalchemy.engine import Engine
from sqlmodel import Session, delete, select

from app.models.segment import Segment
from app.services.subtitles import SegmentData


def replace_all_segments(engine: Engine, job_id: str, segments: list[SegmentData]) -> None:
    with Session(engine) as s:
        s.exec(delete(Segment).where(Segment.job_id == job_id))
        for seg in segments:
            s.add(
                Segment(
                    job_id=job_id,
                    idx=seg.idx,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    avg_logprob=seg.avg_logprob,
                    no_speech_prob=seg.no_speech_prob,
                    edited=False,
                )
            )
        s.commit()


def load_segments(engine: Engine, job_id: str) -> list[SegmentData]:
    with Session(engine) as s:
        rows = s.exec(
            select(Segment).where(Segment.job_id == job_id).order_by(Segment.idx)
        ).all()
    return [
        SegmentData(
            idx=r.idx,
            start=r.start,
            end=r.end,
            text=r.text,
            avg_logprob=r.avg_logprob,
            no_speech_prob=r.no_speech_prob,
        )
        for r in rows
    ]


def load_segments_with_meta(engine: Engine, job_id: str) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(
            select(Segment).where(Segment.job_id == job_id).order_by(Segment.idx)
        ).all()
    return [
        {
            "idx": r.idx,
            "start": r.start,
            "end": r.end,
            "text": r.text,
            "avg_logprob": r.avg_logprob,
            "no_speech_prob": r.no_speech_prob,
            "edited": r.edited,
        }
        for r in rows
    ]


def update_segment(
    engine: Engine,
    job_id: str,
    idx: int,
    text: str | None = None,
    start: float | None = None,
    end: float | None = None,
) -> bool:
    with Session(engine) as s:
        row = s.exec(
            select(Segment).where(Segment.job_id == job_id, Segment.idx == idx)
        ).first()
        if row is None:
            return False
        if text is not None:
            row.text = text
        if start is not None:
            row.start = start
        if end is not None:
            row.end = end
        row.edited = True
        s.add(row)
        s.commit()
    return True


def search_and_replace(
    engine: Engine,
    job_id: str,
    find: str,
    replace: str,
    case_sensitive: bool = False,
) -> int:
    if not find:
        return 0
    with Session(engine) as s:
        rows = s.exec(
            select(Segment).where(Segment.job_id == job_id).order_by(Segment.idx)
        ).all()
        count = 0
        for r in rows:
            if case_sensitive:
                if find in r.text:
                    r.text = r.text.replace(find, replace)
                    r.edited = True
                    count += 1
                    s.add(r)
            else:
                lower = r.text.lower()
                if find.lower() in lower:
                    start_idx = lower.find(find.lower())
                    while start_idx != -1:
                        r.text = r.text[:start_idx] + replace + r.text[start_idx + len(find):]
                        lower = r.text.lower()
                        start_idx = lower.find(find.lower(), start_idx + len(replace))
                    r.edited = True
                    count += 1
                    s.add(r)
        s.commit()
    return count
