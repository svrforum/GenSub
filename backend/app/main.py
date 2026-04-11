import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import router as config_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.core.db import create_db_engine, init_db
from app.core.settings import get_settings
from app.services.cleanup import purge_expired_jobs, sweep_zombie_jobs


async def _cleanup_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            purge_expired_jobs(app.state.engine, app.state.settings)
        except Exception:
            pass


@asynccontextmanager
async def _lifespan(app: FastAPI):
    sweep_zombie_jobs(app.state.engine)
    task = asyncio.create_task(_cleanup_loop(app))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GenSub", version="0.1.0", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_allow_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = create_db_engine(settings.database_url)
    init_db(engine)
    app.state.engine = engine
    app.state.settings = settings

    app.include_router(health_router)
    app.include_router(config_router)
    app.include_router(jobs_router)
    app.include_router(events_router)
    return app
