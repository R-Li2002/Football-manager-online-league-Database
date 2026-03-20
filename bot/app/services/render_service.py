from __future__ import annotations

import time
import re
from pathlib import Path
from urllib.parse import urlencode

from app.config import BotSettings
from app.render.svg_renderer import RenderedImage, SvgPlayerShareRenderer


def _safe_fragment(value: str) -> str:
    normalized = re.sub(r"[\\/:*?\"<>|]+", "_", value.strip())
    normalized = re.sub(r"\s+", "_", normalized).strip("_")
    return normalized or "player"


def build_player_share_url(
    settings: BotSettings,
    uid: int,
    *,
    version: str | None = None,
    step: int = 0,
    theme: str = "dark",
) -> str:
    query = {"step": step, "theme": theme}
    if version:
        query["version"] = version
    return f"{settings.bot_render_base_url}/internal/share/player/{uid}?{urlencode(query)}"


def build_player_share_svg_url(
    settings: BotSettings,
    uid: int,
    *,
    version: str | None = None,
    step: int = 0,
    theme: str = "dark",
) -> str:
    query = {"step": step, "theme": theme}
    if version:
        query["version"] = version
    return f"{settings.bot_render_base_url}/internal/render/player/{uid}.svg?{urlencode(query)}"


def build_player_share_headers(settings: BotSettings) -> dict[str, str]:
    if not settings.internal_share_token:
        return {}
    return {"X-Internal-Share-Token": settings.internal_share_token}


class PlayerShareRenderService:
    def __init__(self, settings: BotSettings, renderer: SvgPlayerShareRenderer | None = None):
        self.settings = settings
        self.output_root = settings.bot_output_path / "player-shares"
        self.renderer = renderer or SvgPlayerShareRenderer(
            output_root=self.output_root,
            timeout_seconds=settings.bot_render_timeout_seconds,
        )

    def _build_file_name(self, *, player_name: str, uid: int, version: str | None, step: int) -> str:
        return f"{_safe_fragment(player_name)}_{uid}_{version or 'default'}_step{step}.png"

    def _resolve_cached_image(self, file_name: str) -> RenderedImage | None:
        target = self.output_root / file_name
        if not target.exists():
            return None
        return RenderedImage(file_path=str(target), file_name=file_name)

    def _is_cache_fresh(self, file_path: str) -> bool:
        ttl = max(0, int(self.settings.bot_render_cache_ttl_seconds))
        if ttl <= 0:
            return False
        age_seconds = time.time() - Path(file_path).stat().st_mtime
        return age_seconds <= ttl

    async def render_player_share(
        self,
        *,
        uid: int,
        player_name: str,
        version: str | None = None,
        step: int = 0,
        theme: str = "dark",
    ) -> tuple[str, RenderedImage]:
        share_url = build_player_share_url(
            self.settings,
            uid,
            version=version,
            step=step,
            theme=theme,
        )
        svg_url = build_player_share_svg_url(
            self.settings,
            uid,
            version=version,
            step=step,
            theme=theme,
        )
        file_name = self._build_file_name(player_name=player_name, uid=uid, version=version, step=step)
        cached = self._resolve_cached_image(file_name)
        if cached and self._is_cache_fresh(cached.file_path):
            return share_url, cached

        try:
            rendered = await self.renderer.render(
                url=svg_url,
                file_name=file_name,
                extra_headers=build_player_share_headers(self.settings),
            )
            return share_url, rendered
        except Exception:
            if cached:
                return share_url, cached
            raise
