from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(prefix="/api", tags=["config"])

AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]


@router.get("/config")
def config() -> dict:
    s = get_settings()
    return {
        "default_model": s.default_model,
        "available_models": AVAILABLE_MODELS,
        "max_video_minutes": s.max_video_minutes,
        "max_upload_mb": s.max_upload_mb,
        "job_ttl_hours": s.job_ttl_hours,
    }
