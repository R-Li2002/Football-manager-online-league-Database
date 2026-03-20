import sys
import tempfile
import time
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.config import BotSettings  # noqa: E402
from app.render.playwright_renderer import RenderedImage  # noqa: E402
from app.services.render_service import PlayerShareRenderService  # noqa: E402


class BotRenderServiceTests(IsolatedAsyncioTestCase):
    async def test_render_service_uses_fresh_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = BotSettings(
                bot_output_root=temp_dir,
                bot_render_cache_ttl_seconds=1800,
            )
            renderer = AsyncMock()
            service = PlayerShareRenderService(settings, renderer=renderer)

            output_dir = Path(temp_dir) / "player-shares"
            output_dir.mkdir(parents=True, exist_ok=True)
            cached_file = output_dir / "Dani_Olmo_24048100_2026-03_step0.png"
            cached_file.write_bytes(b"cached")

            share_url, rendered = await service.render_player_share(
                uid=24048100,
                player_name="Dani Olmo",
                version="2026-03",
                step=0,
            )

            self.assertIn("/internal/share/player/24048100", share_url)
            self.assertEqual(rendered.file_path, str(cached_file))
            renderer.render.assert_not_called()

    async def test_render_service_falls_back_to_stale_cache_on_render_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = BotSettings(
                bot_output_root=temp_dir,
                bot_render_cache_ttl_seconds=1,
            )
            renderer = AsyncMock()
            renderer.render.side_effect = RuntimeError("render failed")
            service = PlayerShareRenderService(settings, renderer=renderer)

            output_dir = Path(temp_dir) / "player-shares"
            output_dir.mkdir(parents=True, exist_ok=True)
            cached_file = output_dir / "Dani_Olmo_24048100_2026-03_step0.png"
            cached_file.write_bytes(b"stale")
            stale_timestamp = time.time() - 60
            Path(cached_file).touch()
            import os
            os.utime(cached_file, (stale_timestamp, stale_timestamp))

            _share_url, rendered = await service.render_player_share(
                uid=24048100,
                player_name="Dani Olmo",
                version="2026-03",
                step=0,
            )

            self.assertEqual(rendered.file_path, str(cached_file))
            renderer.render.assert_called_once()

    async def test_render_service_passes_internal_share_token_header(self):
        settings = BotSettings(
            bot_output_root="output/qqbot",
            internal_share_token="share-secret",
        )
        renderer = AsyncMock()
        renderer.render = AsyncMock(
            return_value=RenderedImage(
                file_path="output/qqbot/player-shares/Dani_Olmo_24048100_default_step0.png",
                file_name="Dani_Olmo_24048100_default_step0.png",
            )
        )
        service = PlayerShareRenderService(settings, renderer=renderer)

        await service.render_player_share(uid=24048100, player_name="Dani Olmo")

        renderer.render.assert_called_once()
        self.assertEqual(
            renderer.render.call_args.kwargs["extra_headers"],
            {"X-Internal-Share-Token": "share-secret"},
        )
