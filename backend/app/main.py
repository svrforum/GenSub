from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.config import router as config_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.media import router as media_router
from app.api.memo import router as memo_router
from app.api.search import router as search_router
from app.api.segments import router as segments_router
from app.core.db import create_db_engine, init_db
from app.core.settings import get_settings
from app.services.backup import backup_database
from app.services.cleanup import sweep_zombie_jobs


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """기동 시 DB 백업 + 좀비 작업(중간에 멈춘 status) 정리.

    NOTE: 자동 만료 삭제(purge_expired_jobs) 는 사용자 요청으로 비활성화.
    Job은 사용자가 명시적으로 DELETE 하기 전까지 보존된다.
    services/cleanup.purge_expired_jobs 함수 자체는 보존돼 있어 향후 필요 시
    수동 호출이나 별도 엔드포인트로 다시 활성화할 수 있다.
    """
    backup_database(app.state.settings)
    sweep_zombie_jobs(app.state.engine)
    yield


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
    app.include_router(media_router)
    app.include_router(segments_router)
    app.include_router(memo_router)
    app.include_router(search_router)

    static_path = settings.static_dir or (Path(__file__).parent / "static")
    if static_path.exists() and (static_path / "index.html").exists():
        app_assets = static_path / "_app"
        if app_assets.exists():
            app.mount(
                "/_app",
                StaticFiles(directory=app_assets),
                name="sveltekit-assets",
            )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404)
            asset = static_path / full_path
            if asset.resolve().is_relative_to(static_path.resolve()) and asset.is_file():
                return FileResponse(asset)
            return FileResponse(static_path / "index.html")

    return app
