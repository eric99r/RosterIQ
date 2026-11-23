from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.db import build_engine, build_session_factory
from app.health import router as health_router
from app.identities.router import router as identities_router
from app.players.router import router as players_router


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = build_engine(get_settings().database_url)
        app.state.session_factory = build_session_factory(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="RosterIQ API", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(players_router, prefix="/api/v1")
    app.include_router(identities_router, prefix="/api/v1")
    return app


app = create_app()
