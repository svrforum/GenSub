from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

import app.models  # noqa: F401  -- 메타데이터 등록 목적 import


def _ensure_parent_dir(url: str) -> None:
    if url.startswith("sqlite:///"):
        path = urlparse(url).path
        if path.startswith("/"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(url: str) -> Engine:
    _ensure_parent_dir(url)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
