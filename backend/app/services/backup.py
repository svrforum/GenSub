"""SQLite DB 백업 유틸리티. api/worker 양쪽 기동 시 호출."""

import shutil
from datetime import datetime
from pathlib import Path

from app.core.settings import Settings

KEEP_RECENT = 3


def backup_database(settings: Settings, *, keep: int = KEEP_RECENT) -> Path | None:
    """현재 DB 파일을 backups/ 디렉토리에 타임스탬프와 함께 복사.

    DB 파일이 없으면 noop(None 반환). 백업 성공 시 백업 파일 경로 반환.
    오래된 백업은 최근 `keep`개만 남기고 삭제.
    """
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    if not db_path.exists():
        return None

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"jobs_{stamp}.db"
    shutil.copy2(db_path, target)

    # 파일명 기준 역순 정렬 = 최신 우선
    existing = sorted(backup_dir.glob("jobs_*.db"), reverse=True)
    for old in existing[keep:]:
        old.unlink(missing_ok=True)

    return target
