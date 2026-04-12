import mimetypes
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel

from app.core.settings import Settings
from app.services import jobs as jobs_service
from app.services.ass_style import BurnStyle
from app.services.clip import export_clip
from app.services.muxer import mux_video_with_subtitles
from app.services.segments import load_segments
from app.services.subtitles import format_json, format_txt

router = APIRouter(prefix="/api/jobs", tags=["media"])

CHUNK_SIZE = 1024 * 512  # 512 KB


def _resolve_source(settings: Settings, job_id: str) -> Path:
    media_dir = settings.media_dir / job_id
    for candidate in sorted(media_dir.glob("source.*")):
        return candidate
    raise HTTPException(status_code=404, detail="source file not found")


def _parse_range(header: str, file_size: int) -> tuple[int, int]:
    unit, _, spec = header.partition("=")
    if unit.strip() != "bytes":
        raise ValueError("unsupported range unit")
    start_s, _, end_s = spec.partition("-")
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else file_size - 1
    if start < 0 or end >= file_size or start > end:
        raise ValueError("range out of bounds")
    return start, end


def _file_iter(path: Path, start: int, end: int) -> Iterator[bytes]:
    remaining = end - start + 1
    with path.open("rb") as f:
        f.seek(start)
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("/{job_id}/video")
def get_video(job_id: str, request: Request) -> Response:
    engine = request.app.state.engine
    settings = request.app.state.settings

    job = jobs_service.get_job(engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    src = _resolve_source(settings, job_id)
    file_size = src.stat().st_size
    content_type = mimetypes.guess_type(str(src))[0] or "video/mp4"
    range_header = request.headers.get("range")

    if range_header is None:
        return StreamingResponse(
            _file_iter(src, 0, file_size - 1),
            media_type=content_type,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            },
        )

    try:
        start, end = _parse_range(range_header, file_size)
    except ValueError as exc:
        raise HTTPException(status_code=416, detail="range not satisfiable") from exc

    length = end - start + 1
    return StreamingResponse(
        _file_iter(src, start, end),
        status_code=206,
        media_type=content_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/{job_id}/subtitles.vtt")
def get_vtt(job_id: str, request: Request) -> FileResponse:
    settings = request.app.state.settings
    path = settings.media_dir / job_id / "subtitles.vtt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="subtitles not ready")
    return FileResponse(path, media_type="text/vtt; charset=utf-8")


@router.get("/{job_id}/subtitles.srt")
def get_srt(job_id: str, request: Request) -> FileResponse:
    settings = request.app.state.settings
    path = settings.media_dir / job_id / "subtitles.srt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="subtitles not ready")
    return FileResponse(
        path,
        media_type="application/x-subrip",
        filename="subtitles.srt",
    )


@router.get("/{job_id}/transcript.txt")
def get_txt(job_id: str, request: Request) -> PlainTextResponse:
    engine = request.app.state.engine
    segments = load_segments(engine, job_id)
    return PlainTextResponse(
        format_txt(segments), media_type="text/plain; charset=utf-8"
    )


@router.get("/{job_id}/transcript.json")
def get_json(job_id: str, request: Request) -> Response:
    engine = request.app.state.engine
    segments = load_segments(engine, job_id)
    return Response(
        content=format_json(segments),
        media_type="application/json; charset=utf-8",
    )


@router.get("/{job_id}/download/video+subs.mkv")
def download_mkv(job_id: str, request: Request) -> FileResponse:
    engine = request.app.state.engine
    settings = request.app.state.settings

    job = jobs_service.get_job(engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    media_dir = settings.media_dir / job_id
    srt = media_dir / "subtitles.srt"
    if not srt.exists():
        raise HTTPException(status_code=404, detail="subtitles not ready")
    src = _resolve_source(settings, job_id)
    output = media_dir / "video+subs.mkv"

    mux_video_with_subtitles(
        video=src,
        subtitle=srt,
        output=output,
        language=job.language or "und",
    )
    return FileResponse(
        output,
        media_type="video/x-matroska",
        headers={"Content-Disposition": 'attachment; filename="video+subs.mkv"'},
    )


@router.get("/{job_id}/download/burned.mp4")
def download_burned(job_id: str, request: Request) -> FileResponse:
    settings = request.app.state.settings
    path = settings.media_dir / job_id / "burned.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="burned file not ready")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="burned.mp4",
    )


class ClipRequest(BaseModel):
    start: float
    end: float
    burn_subtitles: bool = True
    font: str = "Pretendard"
    size: int = 42
    outline: bool = True


@router.post("/{job_id}/clip")
def export_clip_endpoint(
    job_id: str,
    body: ClipRequest,
    request: Request,
) -> FileResponse:
    engine = request.app.state.engine
    settings = request.app.state.settings

    job = jobs_service.get_job(engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    media_dir = settings.media_dir / job_id
    src = _resolve_source(settings, job_id)

    segments = None
    style = None
    if body.burn_subtitles:
        segments = load_segments(engine, job_id)
        style = BurnStyle(font=body.font, size=body.size, outline=body.outline)

    clip_name = f"clip-{body.start:.1f}-{body.end:.1f}.mp4"
    output = media_dir / clip_name

    try:
        export_clip(
            video=src,
            output=output,
            start=body.start,
            end=body.end,
            segments=segments,
            style=style,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(
        output,
        media_type="video/mp4",
        filename=clip_name,
    )
