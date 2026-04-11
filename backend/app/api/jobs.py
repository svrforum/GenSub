from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

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
    file: UploadFile = File(...),
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
