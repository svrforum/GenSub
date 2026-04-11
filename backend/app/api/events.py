import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.services import jobs as jobs_service

router = APIRouter(prefix="/api/jobs", tags=["events"])

TERMINAL_STATES = {"ready", "done", "failed"}
POLL_INTERVAL_SEC = 0.5
MAX_DURATION_SEC = 3600  # 1 hour hard cap on a single SSE subscription


@router.get("/{job_id}/events")
async def events(job_id: str, request: Request):
    engine = request.app.state.engine
    job = jobs_service.get_job(engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_gen():
        last_snapshot = None
        elapsed = 0.0
        while elapsed < MAX_DURATION_SEC:
            if await request.is_disconnected():
                return
            current = jobs_service.get_job(engine, job_id)
            if current is None:
                yield {"event": "error", "data": json.dumps({"message": "job disappeared"})}
                return
            status_val = (
                current.status.value
                if hasattr(current.status, "value")
                else current.status
            )
            snapshot = (
                status_val,
                current.progress,
                current.stage_message,
                current.error_message,
            )
            if snapshot != last_snapshot:
                last_snapshot = snapshot
                if status_val == "failed":
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": current.error_message or "unknown error"}),
                    }
                    return
                yield {
                    "event": "progress",
                    "data": json.dumps(
                        {
                            "status": status_val,
                            "progress": current.progress,
                            "stage_message": current.stage_message,
                        }
                    ),
                }
                if status_val in TERMINAL_STATES:
                    yield {"event": "done", "data": json.dumps({"status": status_val})}
                    return
            await asyncio.sleep(POLL_INTERVAL_SEC)
            elapsed += POLL_INTERVAL_SEC
        yield {"event": "error", "data": json.dumps({"message": "stream timed out"})}

    return EventSourceResponse(event_gen())
