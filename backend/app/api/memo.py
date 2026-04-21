from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.schemas import MemoPatchRequest
from app.services import memo as memo_service

router = APIRouter(tags=["memos"])


def _memo_to_dict(memo) -> dict:
    return {
        "id": memo.id,
        "job_id": memo.job_id,
        "segment_idx": memo.segment_idx,
        "memo_text": memo.memo_text,
        "segment_text_snapshot": memo.segment_text_snapshot,
        "segment_start": memo.segment_start,
        "segment_end": memo.segment_end,
        "job_title_snapshot": memo.job_title_snapshot,
        "created_at": memo.created_at.isoformat(),
        "updated_at": memo.updated_at.isoformat(),
    }


@router.post("/api/jobs/{job_id}/segments/{idx}/memo")
def toggle_memo(job_id: str, idx: int, request: Request, response: Response):
    engine = request.app.state.engine
    try:
        result = memo_service.toggle_save_memo(engine, job_id, idx)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err

    if result.action == "conflict":
        raise HTTPException(
            status_code=409,
            detail={"reason": "memo_has_text", "memo_id": result.memo.id},
        )

    if result.action == "created":
        response.status_code = status.HTTP_201_CREATED
        return {
            "ok": True,
            "action": "created",
            "memo": _memo_to_dict(result.memo),
        }

    return {"ok": True, "action": "deleted"}


@router.patch("/api/memos/{memo_id}")
def patch_memo(memo_id: int, body: MemoPatchRequest, request: Request):
    engine = request.app.state.engine
    updated = memo_service.update_memo_text(engine, memo_id, body.memo_text)
    if updated is None:
        raise HTTPException(status_code=404, detail="memo not found")
    return {"ok": True, "memo": _memo_to_dict(updated)}


@router.get("/api/memos")
def list_memos(request: Request, limit: int = 100):
    engine = request.app.state.engine
    views = memo_service.list_all_memos_with_liveness(engine, limit=limit)
    return {
        "items": [
            {
                "id": v.id,
                "job_id": v.job_id,
                "segment_idx": v.segment_idx,
                "memo_text": v.memo_text,
                "segment_text": v.segment_text,
                "start": v.start,
                "end": v.end,
                "job_title": v.job_title,
                "job_alive": v.job_alive,
                "created_at": v.created_at.isoformat(),
                "updated_at": v.updated_at.isoformat(),
            }
            for v in views
        ]
    }


@router.get("/api/jobs/{job_id}/memos")
def list_memos_for_job(job_id: str, request: Request):
    engine = request.app.state.engine
    memos = memo_service.list_memos_for_job(engine, job_id)
    return {
        "items": [
            {
                "id": m.id,
                "job_id": m.job_id,
                "segment_idx": m.segment_idx,
                "memo_text": m.memo_text,
            }
            for m in memos
        ]
    }


@router.delete("/api/memos/{memo_id}")
def delete_memo(memo_id: int, request: Request):
    engine = request.app.state.engine
    ok = memo_service.delete_memo(engine, memo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="memo not found")
    return {"ok": True}
