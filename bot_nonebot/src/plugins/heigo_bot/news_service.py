from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import html
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import httpx

from .config import BotSettings


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    published: str = ""


class FootballNewsService:
    def __init__(self, settings: BotSettings):
        self.settings = settings
        self._cache: dict[str, tuple[float, list[NewsItem]]] = {}
        self._client = httpx.AsyncClient(timeout=12.0, follow_redirects=True)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_top_news(self) -> list[NewsItem]:
        return await self._fetch_feed("/dongqiudi/top_news")

    async def get_daily(self) -> list[NewsItem]:
        return await self._fetch_feed("/dongqiudi/daily")

    async def _fetch_feed(self, path: str) -> list[NewsItem]:
        now = time.monotonic()
        cached = self._cache.get(path)
        if cached and now - cached[0] < self.settings.news_cache_ttl_seconds:
            return cached[1]

        url = f"{self.settings.news_rsshub_base_url}{path}"
        response = await self._client.get(url)
        response.raise_for_status()
        items = parse_rss_items(response.text)
        self._cache[path] = (now, items)
        return items


class SeenNewsStore:
    def __init__(self, file_path: str | Path, *, max_links: int = 240):
        self.file_path = Path(file_path)
        self.max_links = max_links

    def filter_new(self, feed_key: str, items: list[NewsItem], limit: int) -> list[NewsItem]:
        state = self._load()
        seen_links = list(state.get(feed_key, []))
        seen = set(seen_links)
        fresh: list[NewsItem] = []

        for item in items:
            if item.link in seen:
                continue
            fresh.append(item)
            if len(fresh) >= limit:
                break

        if fresh:
            merged = [item.link for item in fresh] + seen_links
            state[feed_key] = list(dict.fromkeys(merged))[: self.max_links]
            self._save(state)

        return fresh

    def _load(self) -> dict[str, list[str]]:
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        state: dict[str, list[str]] = {}
        for key, value in raw.items():
            if isinstance(key, str) and isinstance(value, list):
                state[key] = [item for item in value if isinstance(item, str)]
        return state

    def _save(self, state: dict[str, list[str]]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_text(value: str | None) -> str:
    return " ".join(html.unescape(value or "").split())


def _format_pub_date(value: str | None) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return raw
    return parsed.strftime("%m-%d %H:%M")


def parse_rss_items(xml_text: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    items: list[NewsItem] = []

    for item in root.findall(".//item"):
        title = _clean_text(item.findtext("title"))
        link = _clean_text(item.findtext("link"))
        published = _format_pub_date(item.findtext("pubDate"))
        if title and link:
            items.append(NewsItem(title=title, link=link, published=published))

    if items:
        return items

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = _clean_text(entry.findtext("atom:title", default="", namespaces=ns))
        link_node = entry.find("atom:link", ns)
        link = _clean_text(link_node.get("href") if link_node is not None else "")
        published = _format_pub_date(entry.findtext("atom:updated", default="", namespaces=ns))
        if title and link:
            items.append(NewsItem(title=title, link=link, published=published))

    return items
