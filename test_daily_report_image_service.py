import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import re

from PIL import Image

from schemas_read import DailyReportResponse
from services import daily_report_image_service


class DailyReportImageServiceTests(unittest.TestCase):
    def test_svg_highlights_score_team_and_player_entities(self):
        report = DailyReportResponse(
            report_date="2026-08-02",
            title="HEIGO 联赛日报｜8月2日",
            content="今日更新 1 场。\n\n【焦点头版】\n阿森纳 2:0 切尔西。",
            focus_content=(
                "今日更新 1 场。\n\n"
                "【焦点头版】\n"
                "【争冠·帽子戏法】超级联赛｜阿森纳 vs 切尔西："
                "第1轮 阿森纳 2:0 切尔西；第2轮 切尔西 1:3 阿森纳。"
                "阿森纳两战全胜。Rodrigo Mora 上演帽子戏法。"
            ),
            fingerprint="semantic-highlight-test",
            match_count=1,
            fixture_group_count=1,
            focus_count=1,
            goal_count=2,
            suspension_count=0,
            generated_at=datetime(2026, 8, 2, 22, 0),
        )

        svg = daily_report_image_service._build_svg(report, scope="focus")

        self.assertIn('data-kind="score"', svg)
        self.assertIn('data-kind="team"', svg)
        self.assertIn('data-kind="player"', svg)
        self.assertIn(">2:0</tspan>", svg)
        self.assertIn(">Rodrigo Mora</tspan>", svg)
        self.assertIn("SECTION 01", svg)
        score_line_match = re.search(r'<text data-role="scoreline"[^>]*>(.*?)</text>', svg)
        self.assertIsNotNone(score_line_match)
        score_line = score_line_match.group(1)
        self.assertIn(">2:0</tspan>", score_line)
        self.assertIn(">1:3</tspan>", score_line)
        self.assertNotIn("Rodrigo Mora", score_line)

    def test_render_png_contains_full_report_and_uses_cache(self):
        report = DailyReportResponse(
            report_date="2026-08-02",
            title="HEIGO 联赛日报｜8月2日",
            content=(
                "今日共更新 4 场比赛，产生 16 粒进球。\n\n"
                "【焦点头版】\n超级联赛｜Alpha vs Beta：第1轮 Alpha 5:1 Beta。Alpha 大胜。\n\n"
                "【常规战报】\n甲级联赛｜Gamma vs Delta：第2轮 Gamma 1:1 Delta。\n\n"
                "【伤停动态】\n超级｜Alpha：Player A（2黄）"
            ),
            focus_content="【焦点头版】\nAlpha 5:1 Beta。",
            fingerprint="image-test-fingerprint",
            match_count=4,
            fixture_group_count=3,
            focus_count=1,
            goal_count=16,
            suspension_count=1,
            generated_at=datetime(2026, 8, 2, 22, 0),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            first = daily_report_image_service.render_daily_report_png(report, temp_dir)
            second = daily_report_image_service.render_daily_report_png(report, temp_dir)
            self.assertEqual(first.cache_status, "MISS")
            self.assertEqual(second.cache_status, "HIT")
            self.assertEqual(first.etag, second.etag)
            self.assertIn("_tpl6.png", first.file_name)
            self.assertTrue(Path(first.file_path).exists())
            with Image.open(first.file_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.width, 1200)
                self.assertGreaterEqual(image.height, 820)

    def test_focus_render_uses_a_separate_shorter_cache_entry(self):
        report = DailyReportResponse(
            report_date="2026-08-02",
            title="HEIGO 联赛日报｜8月2日",
            content="今日更新 10 场。\n\n【焦点头版】\n焦点一。\n\n【常规战报】\n" + "\n".join(f"常规比赛 {index}。" for index in range(20)),
            focus_content="今日更新 10 场。\n\n【焦点头版】\n【争冠】阿森纳 2:0 切尔西。\n【保级】马赛 1:0 里昂。",
            fingerprint="focus-image-fingerprint",
            match_count=10,
            fixture_group_count=5,
            focus_count=2,
            goal_count=24,
            suspension_count=3,
            generated_at=datetime(2026, 8, 2, 22, 0),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            full = daily_report_image_service.render_daily_report_png(report, temp_dir, scope="full")
            focus = daily_report_image_service.render_daily_report_png(report, temp_dir, scope="focus")
            self.assertNotEqual(full.file_name, focus.file_name)
            with Image.open(full.file_path) as full_image, Image.open(focus.file_path) as focus_image:
                self.assertLess(focus_image.height, full_image.height)
                self.assertEqual(focus_image.width, 1200)

    def test_focus_svg_keeps_the_last_sentence_of_long_edited_content(self):
        last_sentence = "人工编辑的最后一句必须完整出现在焦点图片中。"
        report = DailyReportResponse(
            report_date="2026-08-02",
            title="HEIGO 联赛日报｜8月2日",
            content="今日更新 1 场。",
            focus_content=(
                "今日更新 1 场。\n\n【焦点头版】\n"
                "【争冠】超级联赛｜阿森纳 vs 切尔西：阿森纳 2:0 切尔西。"
                + "双方围绕中场展开了漫长而激烈的争夺。" * 35
                + last_sentence
            ),
            fingerprint="long-edited-focus-content",
            match_count=1,
            fixture_group_count=1,
            focus_count=1,
            goal_count=2,
            suspension_count=0,
            generated_at=datetime(2026, 8, 2, 22, 0),
        )

        svg = daily_report_image_service._build_svg(report, scope="focus")
        height_match = re.search(r'<svg[^>]*height="(\d+)"', svg)
        rendered_text = re.sub(r"<[^>]+>", "", svg)

        self.assertIn(last_sentence, rendered_text)
        self.assertIsNotNone(height_match)
        self.assertGreater(int(height_match.group(1)), 820)


if __name__ == "__main__":
    unittest.main()
