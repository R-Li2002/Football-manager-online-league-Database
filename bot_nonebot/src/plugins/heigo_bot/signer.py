from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from urllib.parse import quote, urlencode


@dataclass(frozen=True)
class RenderUrlSigner:
    render_base_url: str
    signing_key: str
    ttl_seconds: int = 90
    theme: str = "dark"

    @staticmethod
    def _normalize_theme(theme: str | None) -> str:
        return "light" if theme == "light" else "dark"

    @staticmethod
    def _normalize_step(step: int | None) -> int:
        return max(0, min(5, int(step or 0)))

    @staticmethod
    def _normalize_page(page: int | None) -> int:
        return max(1, min(20, int(page or 1)))

    def _sign(self, payload: str) -> str:
        digest = hmac.new(self.signing_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def _exp(self) -> int:
        return int(time.time()) + max(30, int(self.ttl_seconds))

    def build_player_png_url(self, uid: int, *, version: str | None = None, step: int = 0, theme: str | None = None) -> str:
        exp = self._exp()
        normalized_theme = self._normalize_theme(theme or self.theme)
        payload = (
            f"type=player&uid={int(uid)}&version={(version or '').strip()}&step={self._normalize_step(step)}&theme={normalized_theme}&exp={exp}"
        )
        query = {"step": self._normalize_step(step), "theme": normalized_theme, "exp": exp, "sig": self._sign(payload)}
        if version:
            query["version"] = version
        return f"{self.render_base_url}/internal/render/player/{int(uid)}.png?{urlencode(query)}"

    def build_wage_png_url(self, uid: int, *, theme: str | None = None) -> str:
        exp = self._exp()
        normalized_theme = self._normalize_theme(theme or self.theme)
        payload = f"type=wage&uid={int(uid)}&theme={normalized_theme}&exp={exp}"
        query = {"theme": normalized_theme, "exp": exp, "sig": self._sign(payload)}
        return f"{self.render_base_url}/internal/render/wage/{int(uid)}.png?{urlencode(query)}"

    def build_roster_png_url(self, team_name: str, *, page: int = 1, theme: str | None = None) -> str:
        exp = self._exp()
        normalized_theme = self._normalize_theme(theme or self.theme)
        normalized_page = self._normalize_page(page)
        payload = f"type=roster&team={(team_name or '').strip()}&page={normalized_page}&theme={normalized_theme}&exp={exp}"
        query = {"team": team_name, "page": normalized_page, "theme": normalized_theme, "exp": exp, "sig": self._sign(payload)}
        return f"{self.render_base_url}/internal/render/roster.png?{urlencode(query)}"
