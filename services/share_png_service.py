from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

try:
    import cairosvg
except ImportError:  # pragma: no cover - exercised via runtime environment
    cairosvg = None

from schemas_read import PlayerAttributeDetailResponse, PlayerResponse, TeamInfoResponse, WageDetailResponse
from services import share_svg_renderer


@dataclass(frozen=True)
class RenderedSharePng:
    file_path: str
    file_name: str
    etag: str
    cache_status: str


class SharePngRenderer:
    def __init__(self, cache_root: str | Path, *, template_version: int = 2):
        self.cache_root = Path(cache_root)
        self.template_version = int(template_version)

    @staticmethod
    def _normalize_theme(theme: str | None) -> str:
        return "light" if theme == "light" else "dark"

    @staticmethod
    def _normalize_step(step: int | None) -> int:
        return max(0, min(5, int(step or 0)))

    @staticmethod
    def _normalize_page(page: int | None) -> int:
        return max(1, min(20, int(page or 1)))

    @staticmethod
    def _slug(value: str) -> str:
        normalized = "_".join((value or "").strip().split())
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in normalized)
        return safe.strip("_") or "item"

    @staticmethod
    def _build_etag(cache_key: str) -> str:
        return hashlib.md5(cache_key.encode("utf-8")).hexdigest()

    def _build_cache_key(self, kind: str, *parts: str) -> str:
        return f"{kind}_{'_'.join(parts)}_tpl{self.template_version}"

    def _build_target_path(self, kind: str, cache_key: str) -> Path:
        return self.cache_root / kind / f"{cache_key}.png"

    def _render_png(self, *, kind: str, cache_key: str, svg: str) -> RenderedSharePng:
        target = self._build_target_path(kind, cache_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        etag = self._build_etag(cache_key)
        if target.exists():
            return RenderedSharePng(
                file_path=str(target),
                file_name=target.name,
                etag=etag,
                cache_status="HIT",
            )
        if cairosvg is None:
            raise RuntimeError("cairosvg_not_installed")
        png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"))
        target.write_bytes(png_bytes)
        return RenderedSharePng(
            file_path=str(target),
            file_name=target.name,
            etag=etag,
            cache_status="MISS",
        )

    def render_player_png(
        self,
        player: PlayerAttributeDetailResponse,
        *,
        version: str,
        step: int = 0,
        theme: str = "dark",
    ) -> RenderedSharePng:
        cache_key = self._build_cache_key(
            "player",
            str(int(player.uid)),
            self._slug(version or "default"),
            f"step{self._normalize_step(step)}",
            self._normalize_theme(theme),
        )
        svg = share_svg_renderer.build_player_share_svg(
            player,
            version=version,
            step=step,
            theme=theme,
        )
        return self._render_png(kind="player", cache_key=cache_key, svg=svg)

    def render_wage_png(
        self,
        player: PlayerAttributeDetailResponse,
        wage_detail: WageDetailResponse,
        *,
        theme: str = "dark",
    ) -> RenderedSharePng:
        cache_key = self._build_cache_key(
            "wage",
            str(int(player.uid)),
            self._normalize_theme(theme),
        )
        svg = share_svg_renderer.build_wage_share_svg(player, wage_detail, theme=theme)
        return self._render_png(kind="wage", cache_key=cache_key, svg=svg)

    def render_roster_png(
        self,
        team_name: str,
        players: list[PlayerResponse],
        *,
        team_info: TeamInfoResponse | None = None,
        page: int = 1,
        theme: str = "dark",
    ) -> RenderedSharePng:
        team_hash = hashlib.md5((team_name or "").encode("utf-8")).hexdigest()[:10]
        cache_key = self._build_cache_key(
            "roster",
            self._slug(team_name),
            team_hash,
            f"page{self._normalize_page(page)}",
            self._normalize_theme(theme),
        )
        svg = share_svg_renderer.build_roster_share_svg(
            team_name,
            players,
            team_info=team_info,
            page=page,
            theme=theme,
        )
        return self._render_png(kind="roster", cache_key=cache_key, svg=svg)
