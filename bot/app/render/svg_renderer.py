from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from app.utils.logging import get_logger

try:  # pragma: no cover - optional dependency is exercised in runtime/tests
    import cairosvg
except ImportError:  # pragma: no cover
    cairosvg = None


logger = get_logger(__name__)


@dataclass(frozen=True)
class RenderedImage:
    file_path: str
    file_name: str
    mime_type: str = "image/png"
    width: int = 1440
    height: int = 1280


class SvgPlayerShareRenderer:
    def __init__(self, *, output_root: Path, timeout_seconds: float = 20.0):
        self.output_root = output_root
        self.timeout_seconds = timeout_seconds

    async def render(
        self,
        *,
        url: str,
        file_name: str,
        extra_headers: dict[str, str] | None = None,
    ) -> RenderedImage:
        self.output_root.mkdir(parents=True, exist_ok=True)
        target_path = self.output_root / file_name

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=extra_headers)
            response.raise_for_status()

        if cairosvg is None:  # pragma: no cover
            raise RuntimeError("CairoSVG Python package not installed")

        png_bytes = cairosvg.svg2png(
            bytestring=response.content,
            output_width=1440,
            output_height=1280,
        )
        target_path.write_bytes(png_bytes)
        logger.info("Rendered player share PNG to %s from %s", target_path, url)
        return RenderedImage(file_path=str(target_path), file_name=file_name)
