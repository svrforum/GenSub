from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.api.schemas import JobCreateRequest
from app.services import jobs as jobs_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job(body: JobCreateRequest, request: Request) -> dict:
    if not body.url:
        raise HTTPException(status_code=422, detail="url is required for URL-based jobs")

    engine = request.app.state.engine
    settings = request.app.state.settings
    job = jobs_service.create_job_from_url(
        engine=engine,
        settings=settings,
        url=body.url,
        model=body.model,
        language=body.language,
        initial_prompt=body.initial_prompt,
    )
    return {"job_id": job.id, "status": job.status.value}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_job(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    model: str = Form("small"),
    language: str | None = Form(None),
    initial_prompt: str | None = Form(None),
) -> dict:
    settings = request.app.state.settings
    engine = request.app.state.engine

    job, dest = jobs_service.create_job_from_upload(
        engine=engine,
        settings=settings,
        filename=file.filename or "upload.mp4",
        model=model,
        language=language,
        initial_prompt=initial_prompt,
    )

    # Stream file to disk in chunks instead of buffering the whole upload in memory
    chunk_limit = settings.max_upload_mb * 1024 * 1024
    size = 0
    try:
        with dest.open("wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                size += len(chunk)
                if size > chunk_limit:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"file exceeds {settings.max_upload_mb}MB limit",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    return {"job_id": job.id, "status": job.status.value}


@router.get("")
def list_jobs(request: Request, limit: int = 20) -> dict:
    """만료되지 않은 최근 작업 리스트. 사이드바 복구용."""
    jobs = jobs_service.list_recent_jobs(request.app.state.engine, limit=limit)
    return {"jobs": [jobs_service.job_to_dict(j) for j in jobs]}


@router.get("/{job_id}")
def get_job(job_id: str, request: Request) -> dict:
    job = jobs_service.get_job(request.app.state.engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return jobs_service.job_to_dict(job)


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, request: Request) -> dict:
    ok = jobs_service.request_cancel(request.app.state.engine, job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True}


@router.delete("/{job_id}")
def delete_job_handler(job_id: str, request: Request) -> dict:
    ok = jobs_service.delete_job(
        request.app.state.engine, request.app.state.settings, job_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True}


@router.post("/{job_id}/pin")
def pin_job(job_id: str, request: Request) -> dict:
    new_pinned = jobs_service.toggle_pin(request.app.state.engine, job_id)
    if new_pinned is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True, "pinned": new_pinned}


class BurnRequest(BaseModel):
    font: str = "Pretendard"
    size: int = 42
    outline: bool = True


@router.post("/{job_id}/burn")
def trigger_burn(job_id: str, body: BurnRequest, request: Request) -> dict:
    # body(font/size/outline)는 현재 worker에서 무시되는 미사용 파라미터.
    # 계약 유지를 위해 시그니처만 남김.
    try:
        jobs_service.request_burn(request.app.state.engine, job_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail="job not found") from err
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err
    return {"ok": True}
