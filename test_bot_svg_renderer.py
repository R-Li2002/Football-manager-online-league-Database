import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import httpx


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.render.svg_renderer import SvgPlayerShareRenderer  # noqa: E402


class BotSvgRendererTests(IsolatedAsyncioTestCase):
    async def test_svg_renderer_fetches_svg_and_writes_png(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = SvgPlayerShareRenderer(output_root=Path(temp_dir), timeout_seconds=5)
            request = httpx.Request("GET", "http://heigo.test/internal/render/player/1.svg")
            response = httpx.Response(
                200,
                request=request,
                text="<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>",
            )

            with patch("app.render.svg_renderer.httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
                with patch(
                    "app.render.svg_renderer.cairosvg",
                    new=SimpleNamespace(svg2png=lambda **_: b"png-bytes"),
                ):
                    rendered = await renderer.render(
                        url="http://heigo.test/internal/render/player/1.svg",
                        file_name="sample.png",
                        extra_headers={"X-Internal-Share-Token": "share-secret"},
                    )

            self.assertTrue(Path(rendered.file_path).exists())
            self.assertEqual(Path(rendered.file_path).read_bytes(), b"png-bytes")

    async def test_svg_renderer_raises_when_rasterization_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = SvgPlayerShareRenderer(output_root=Path(temp_dir), timeout_seconds=5)
            request = httpx.Request("GET", "http://heigo.test/internal/render/player/1.svg")
            response = httpx.Response(
                200,
                request=request,
                text="<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>",
            )

            with patch("app.render.svg_renderer.httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
                with patch(
                    "app.render.svg_renderer.cairosvg",
                    new=SimpleNamespace(svg2png=lambda **_: (_ for _ in ()).throw(RuntimeError("bad svg"))),
                ):
                    with self.assertRaises(RuntimeError):
                        await renderer.render(
                            url="http://heigo.test/internal/render/player/1.svg",
                            file_name="sample.png",
                        )
