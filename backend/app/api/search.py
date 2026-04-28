from fastapi import APIRouter, Request

from app.services import search as search_service

router = APIRouter(tags=["search"])


def _hit_to_dict(hit) -> dict:
    """SearchHit dataclass → JSON-friendly dict (None 필드 제외)."""
    out: dict = {
        "kind": hit.kind,
        "job_id": hit.job_id,
        "job_title": hit.job_title,
    }
    if hit.segment_idx is not None:
        out["segment_idx"] = hit.segment_idx
    if hit.segment_text is not None:
        out["segment_text"] = hit.segment_text
    if hit.start is not None:
        out["start"] = hit.start
    if hit.end is not None:
        out["end"] = hit.end
    if hit.memo_id is not None:
        out["memo_id"] = hit.memo_id
    if hit.memo_text is not None:
        out["memo_text"] = hit.memo_text
    return out


@router.get("/api/search")
def search(request: Request, q: str = "", limit: int = 50) -> dict:
    hits = search_service.search_all(request.app.state.engine, q, limit=limit)
    return {"items": [_hit_to_dict(h) for h in hits]}
