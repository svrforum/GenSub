import mimetypes
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from app.core.settings import Settings
from app.services import jobs as jobs_service

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
