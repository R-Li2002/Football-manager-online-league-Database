from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class HeigoClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_health(self) -> dict[str, Any]:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

    async def search_players(self, player_name: str) -> list[dict[str, Any]]:
        response = await self._client.get(f"/api/players/search/{quote(player_name, safe='')}")
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
