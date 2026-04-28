from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gensub_role: Literal["api", "worker"] = "api"
    database_url: str = "sqlite:////data/db/jobs.db"
    media_dir: Path = Path("/data/media")
    model_cache_dir: Path = Path("/data/models")

    job_ttl_hours: int = Field(default=24, ge=1)
    max_video_minutes: int = Field(default=90, ge=1)
    default_model: str = "small"
    compute_type: Literal["int8", "int8_float16", "float16", "float32"] = "int8"
    worker_concurrency: int = Field(default=1, ge=1, le=8)

    cors_allow_origin: str = "*"

    max_upload_mb: int = Field(default=2048, ge=1)

    static_dir: Path | None = None


def get_settings() -> Settings:
    return Settings()
