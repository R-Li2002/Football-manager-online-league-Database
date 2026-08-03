from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

import httpx


class HeigoApiClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0, render_base_url: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.render_base_url = (render_base_url or base_url).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_health(self) -> dict[str, Any]:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

    async def get_daily_report(self, report_date: str | None = None) -> dict[str, Any]:
        params = {"report_date": report_date} if report_date else None
        response = await self._client.get("/api/daily-report", params=params)
        response.raise_for_status()
        return response.json()

    def get_daily_report_image_url(
        self,
        report_date: str | None = None,
        fingerprint: str | None = None,
        *,
        focus_only: bool = False,
    ) -> str:
        query: dict[str, str] = {}
        if report_date:
            query["report_date"] = report_date
        if fingerprint:
            query["fingerprint"] = fingerprint[:16]
        if focus_only:
            query["scope"] = "focus"
        suffix = f"?{urlencode(query)}" if query else ""
        return f"{self.render_base_url}/api/daily-report/image{suffix}"

    async def warm_daily_report_image(
        self,
        report_date: str,
        fingerprint: str | None = None,
        *,
        focus_only: bool = True,
    ) -> str:
        params: dict[str, str] = {"report_date": report_date}
        if fingerprint:
            params["fingerprint"] = fingerprint[:16]
        if focus_only:
            params["scope"] = "focus"
        async with self._client.stream("GET", "/api/daily-report/image", params=params) as response:
            response.raise_for_status()
            return str(response.headers.get("X-Render-Cache") or "ok")

    async def get_standings(self, level: str) -> dict[str, Any]:
        response = await self._client.get("/api/standings", params={"level": level})
        response.raise_for_status()
        return response.json()

    async def get_suspensions(self, level: str) -> dict[str, Any]:
        response = await self._client.get("/api/suspensions", params={"level": level})
        response.raise_for_status()
        return response.json()

    async def get_rankings(self) -> dict[str, Any]:
        response = await self._client.get("/api/rankings")
        response.raise_for_status()
        return response.json()

    async def get_player_rankings(self, level: str) -> dict[str, Any]:
        response = await self._client.get("/api/player-rankings", params={"level": level})
        response.raise_for_status()
        return response.json()

    def get_league_report_image_url(self, kind: str, level: str, fingerprint: str | None = None) -> str:
        params = {"kind": kind, "level": level}
        if fingerprint:
            params["fingerprint"] = fingerprint[:16]
        query = urlencode(params)
        return f"{self.render_base_url}/api/league-report/image?{query}"

    def get_statistics_report_image_url(
        self,
        kind: str,
        *,
        level: str | None = None,
        metric: str | None = None,
        fingerprint: str | None = None,
    ) -> str:
        params = {"kind": kind}
        if level:
            params["level"] = level
        if metric:
            params["metric"] = metric
        if fingerprint:
            params["fingerprint"] = fingerprint[:16]
        return f"{self.render_base_url}/api/statistics-report/image?{urlencode(params)}"

    async def get_teams(self) -> list[dict[str, Any]]:
        response = await self._client.get("/api/teams")
        response.raise_for_status()
        return response.json()

    async def search_player_attributes(self, player_name: str, version: str | None = None) -> list[dict[str, Any]]:
        params = {"version": version} if version else None
        response = await self._client.get(f"/api/attributes/search/{quote(player_name, safe='')}", params=params)
        response.raise_for_status()
        return response.json()

    async def get_player_attribute_detail(self, uid: int, version: str | None = None) -> dict[str, Any] | None:
        params = {"version": version} if version else None
        response = await self._client.get(f"/api/attributes/{uid}", params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def get_players_by_team(self, team_name: str) -> list[dict[str, Any]]:
        response = await self._client.get(f"/api/players/team/{quote(team_name, safe='')}")
        response.raise_for_status()
        return response.json()

    async def get_player_wage_detail(self, uid: int) -> dict[str, Any]:
        response = await self._client.get(f"/api/player/wage-detail/{uid}")
        response.raise_for_status()
        return response.json()
