from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.clients.heigo_client import HeigoClient
from app.config import BotSettings
from app.services.command_service import parse_command
from app.services.render_service import PlayerShareRenderService
from app.services.reply_service import build_reply


def build_internal_debug_router(
    settings: BotSettings,
    heigo_client: HeigoClient,
    render_service: PlayerShareRenderService,
) -> APIRouter:
    router = APIRouter()

    @router.get("/internal/debug/command")
    async def debug_command(q: str):
        command = parse_command(q)
        try:
            reply = await build_reply(command, heigo_client, settings, render_service)
        except Exception as exc:  # pragma: no cover - debug fallback
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"command": command.model_dump(), "reply": reply.model_dump()}

    @router.post("/internal/render/player")
    async def debug_render_player(uid: int, version: str | None = None, step: int = 0, name: str = "player"):
        share_url, rendered = await render_service.render_player_share(
            uid=uid,
            player_name=name,
            version=version,
            step=step,
        )
        return {"share_url": share_url, "rendered": rendered.__dict__}

    return router
