from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class RenderedImage:
    file_path: str
    file_name: str
    mime_type: str = "image/png"
    width: int = 1440
    height: int = 1600


class PlaywrightPlayerShareRenderer:
    def __init__(self, *, output_root: Path, timeout_seconds: float = 20.0, headless: bool = True):
        self.output_root = output_root
        self.timeout_seconds = timeout_seconds
        self.headless = headless

    async def render(
        self,
        *,
        url: str,
        file_name: str,
        locator: str = ".card",
        extra_headers: dict[str, str] | None = None,
    ) -> RenderedImage:
        self.output_root.mkdir(parents=True, exist_ok=True)
        target_path = self.output_root / file_name

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Playwright Python package not installed") from exc

        timeout_ms = int(self.timeout_seconds * 1000)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless)
            try:
                page = await browser.new_page(
                    viewport={"width": 1440, "height": 1600},
                    device_scale_factor=2,
                )
                if extra_headers:
                    await page.set_extra_http_headers(extra_headers)
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                await page.locator(locator).wait_for(state="visible", timeout=timeout_ms)
                await page.screenshot(path=str(target_path), full_page=True)
            finally:
                await browser.close()

        logger.info("Rendered player share image to %s", target_path)
        return RenderedImage(file_path=str(target_path), file_name=file_name)
