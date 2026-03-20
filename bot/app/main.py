from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.heigo_client import HeigoClient
from app.clients.onebot_client import OneBotClient
from app.config import BotSettings
from app.routers.internal_debug_routes import build_internal_debug_router
from app.routers.onebot_routes import build_onebot_router
from app.services.rate_limit_service import InMemoryRateLimitService
from app.services.render_service import PlayerShareRenderService


def create_app(settings: BotSettings | None = None) -> FastAPI:
    active_settings = settings or BotSettings.from_env()
    heigo_client = HeigoClient(
        base_url=active_settings.heigo_base_url,
        timeout_seconds=active_settings.heigo_timeout_seconds,
    )
    onebot_client = OneBotClient(active_settings)
    rate_limit_service = InMemoryRateLimitService()
    render_service = PlayerShareRenderService(active_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            await heigo_client.aclose()
            await onebot_client.aclose()

    app = FastAPI(title="HEIGO QQ Bot", lifespan=lifespan)
    app.state.settings = active_settings
    app.include_router(
        build_onebot_router(
            active_settings,
            heigo_client,
            onebot_client,
            rate_limit_service,
            render_service,
        )
    )
    app.include_router(build_internal_debug_router(active_settings, heigo_client, render_service))
    return app


app = create_app()
