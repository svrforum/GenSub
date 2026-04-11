from sqlalchemy import text

from app.core.db import create_db_engine, init_db


def test_init_db_creates_tables_and_enables_wal(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_db_engine(url)
    init_db(engine)

    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert mode.lower() == "wal"

        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        assert "job" in tables
        assert "segment" in tables
