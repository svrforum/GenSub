import signal
import time

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings, get_settings
from app.models.job import Job, JobStatus
from app.services import job_state
from app.services.backup import backup_database
from app.services.cleanup import sweep_zombie_jobs
from app.services.pipeline import process_burn_job, process_job

POLL_INTERVAL_SEC = 1.5

_stop_requested = False


def _handle_signal(*_args) -> None:
    global _stop_requested  # noqa: PLW0603
    _stop_requested = True


def _find_burn_candidate(engine: Engine) -> Job | None:
    with Session(engine) as s:
        return s.exec(
            select(Job)
            .where(Job.status == JobStatus.burning)
            .where(Job.progress == 0.0)
            .order_by(Job.updated_at)
        ).first()


def tick(settings: Settings, engine: Engine) -> bool:
    burn = _find_burn_candidate(engine)
    if burn is not None:
        print(f"[worker] burn job {burn.id[:8]}...", flush=True)
        process_burn_job(settings=settings, engine=engine, job_id=burn.id)
        print(f"[worker] burn job {burn.id[:8]}... done", flush=True)
        return True

    claimed = job_state.claim_next_pending_job(engine)
    if claimed is not None:
        print(f"[worker] processing job {claimed.id[:8]}...", flush=True)
        process_job(settings=settings, engine=engine, job_id=claimed.id)
        print(f"[worker] job {claimed.id[:8]}... done", flush=True)
        return True

    return False


def run() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    backup_database(settings)

    swept = sweep_zombie_jobs(engine)
    if swept:
        print(f"[worker] swept {swept} zombie job(s)", flush=True)

    print(
        f"[worker] starting (role={settings.gensub_role}, "
        f"model={settings.default_model})",
        flush=True,
    )

    while not _stop_requested:
        try:
            did_work = tick(settings, engine)
        except Exception as exc:
            print(f"[worker] tick error: {exc}", flush=True)
            did_work = False
        if not did_work:
            time.sleep(POLL_INTERVAL_SEC)

    print("[worker] shutting down", flush=True)


if __name__ == "__main__":
    run()
