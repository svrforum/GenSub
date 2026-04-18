from datetime import datetime, timedelta
from pathlib import Path

from app.core.settings import Settings
from app.services.backup import backup_database


def _make_settings(db_path: Path) -> Settings:
    # Settings는 env-driven이지만 생성자 kwargs로 override 가능
    return Settings(
        database_url=f"sqlite:///{db_path}",
        media_dir=db_path.parent / "media",
        model_cache_dir=db_path.parent / "models",
    )


def test_backup_creates_backup_file(tmp_path):
    db_path = tmp_path / "jobs.db"
    db_path.write_bytes(b"fake db content")
    settings = _make_settings(db_path)

    result = backup_database(settings)

    backup_dir = tmp_path / "backups"
    assert backup_dir.exists()
    backups = list(backup_dir.glob("jobs_*.db"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"fake db content"
    assert result == backups[0]


def test_backup_keeps_only_recent_three(tmp_path):
    db_path = tmp_path / "jobs.db"
    db_path.write_bytes(b"x")
    settings = _make_settings(db_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # 4개의 오래된 백업 미리 세팅 (서로 다른 timestamp, 과거)
    old_times = [
        datetime.now() - timedelta(hours=i) for i in [10, 8, 6, 4]
    ]
    for t in old_times:
        stamp = t.strftime("%Y%m%d_%H%M%S")
        (backup_dir / f"jobs_{stamp}.db").write_bytes(b"old")

    backup_database(settings)

    # 새로 만든 것 1개 + 기존 중 최근 2개 = 3개
    backups = sorted(backup_dir.glob("jobs_*.db"))
    assert len(backups) == 3


def test_backup_noop_when_db_missing(tmp_path):
    db_path = tmp_path / "jobs.db"  # 존재하지 않음
    settings = _make_settings(db_path)

    result = backup_database(settings)

    assert result is None
    backup_dir = tmp_path / "backups"
    # 디렉토리 없거나 있어도 빈 상태
    if backup_dir.exists():
        assert list(backup_dir.glob("jobs_*.db")) == []
