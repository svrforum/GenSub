from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.schemas import JobCreateRequest
from app.models.job import Job, JobStatus
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

    max_bytes = settings.max_upload_mb * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"file exceeds {settings.max_upload_mb} MB")

    job, dest = jobs_service.create_job_from_upload(
        engine=engine,
        settings=settings,
        filename=file.filename or "upload.mp4",
        model=model,
        language=language,
        initial_prompt=initial_prompt,
    )
    dest.write_bytes(contents)
    return {"job_id": job.id, "status": job.status.value}


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


class BurnRequest(BaseModel):
    font: str = "Pretendard"
    size: int = 42
    outline: bool = True


@router.post("/{job_id}/burn")
def trigger_burn(job_id: str, body: BurnRequest, request: Request) -> dict:
    engine = request.app.state.engine
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if job.status not in (JobStatus.ready, JobStatus.done):
            raise HTTPException(
                status_code=409,
                detail=f"cannot burn from status {job.status.value}",
            )
        job.status = JobStatus.burning
        job.progress = 0.0
        job.stage_message = "자막을 영상에 입히고 있어요"
        job.updated_at = datetime.now(UTC)
        s.add(job)
        s.commit()
    return {"ok": True}
