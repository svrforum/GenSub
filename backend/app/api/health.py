import shutil
from pathlib import Path

from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(prefix="/api", tags=["health"])


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


@router.get("/health")
def health() -> dict:
    s = get_settings()
    s.media_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(s.media_dir)
    return {
        "ok": True,
        "disk_free": usage.free,
        "model_cache_size": _dir_size(s.model_cache_dir),
        "role": s.gensub_role,
    }
