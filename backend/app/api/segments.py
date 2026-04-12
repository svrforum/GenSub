from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import (
    SearchReplaceRequest,
    SearchReplaceResponse,
    SegmentPatchRequest,
)
from app.core.settings import Settings
from app.services import jobs as jobs_service
from app.services.segments import (
    load_segments,
    load_segments_with_meta,
    search_and_replace,
    update_segment,
)
from app.services.subtitles import format_srt, format_vtt

router = APIRouter(prefix="/api/jobs", tags=["segments"])


def _rewrite_subtitle_files(settings: Settings, job_id: str, engine) -> None:
    segments = load_segments(engine, job_id)
    media_dir = settings.media_dir / job_id
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "subtitles.srt").write_text(format_srt(segments), encoding="utf-8")
    (media_dir / "subtitles.vtt").write_text(format_vtt(segments), encoding="utf-8")


@router.get("/{job_id}/segments")
def list_segments(job_id: str, request: Request) -> list[dict]:
    engine = request.app.state.engine
    if jobs_service.get_job(engine, job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return load_segments_with_meta(engine, job_id)


@router.patch("/{job_id}/segments/{idx}")
def patch_segment(
    job_id: str,
    idx: int,
    body: SegmentPatchRequest,
    request: Request,
) -> dict:
    engine = request.app.state.engine
    settings = request.app.state.settings
    if jobs_service.get_job(engine, job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")

    ok = update_segment(
        engine,
        job_id,
        idx,
        text=body.text,
        start=body.start,
        end=body.end,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="segment not found")
    _rewrite_subtitle_files(settings, job_id, engine)
    return {"ok": True}


@router.post("/{job_id}/search_replace")
def search_replace(
    job_id: str,
    body: SearchReplaceRequest,
    request: Request,
) -> SearchReplaceResponse:
    engine = request.app.state.engine
    settings = request.app.state.settings
    if jobs_service.get_job(engine, job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")

    changed = search_and_replace(
        engine, job_id, body.find, body.replace, body.case_sensitive
    )
    if changed:
        _rewrite_subtitle_files(settings, job_id, engine)
    return SearchReplaceResponse(changed_count=changed)
