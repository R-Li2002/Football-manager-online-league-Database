import sys
import unittest
from pathlib import Path


BOT_PLUGIN_PARENT = Path(__file__).resolve().parent / "bot_nonebot" / "src" / "plugins"
if str(BOT_PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(BOT_PLUGIN_PARENT))

from heigo_bot.news_service import NewsItem, SeenNewsStore, parse_rss_items  # noqa: E402


class BotNewsServiceTests(unittest.TestCase):
    def test_parse_rss_items(self):
        items = parse_rss_items(
            """<?xml version="1.0" encoding="UTF-8" ?>
            <rss version="2.0">
              <channel>
                <item>
                  <title>球队&amp;教练动态</title>
                  <link>https://example.com/a</link>
                  <pubDate>Fri, 19 Jun 2026 01:30:00 GMT</pubDate>
                </item>
              </channel>
            </rss>
            """
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "球队&教练动态")
        self.assertEqual(items[0].link, "https://example.com/a")
        self.assertEqual(items[0].published, "06-19 01:30")

    def test_seen_news_store_filters_and_persists_seen_links(self):
        store_path = Path("/tmp/heigo-test-news-state.json")
        try:
            store_path.unlink()
        except FileNotFoundError:
            pass

        store = SeenNewsStore(store_path, max_links=3)
        items = [
            NewsItem("A", "https://example.com/a"),
            NewsItem("B", "https://example.com/b"),
            NewsItem("C", "https://example.com/c"),
        ]
        first = store.filter_new("top", items, 2)
        self.assertEqual([item.link for item in first], ["https://example.com/a", "https://example.com/b"])

        second = store.filter_new("top", items, 3)
        self.assertEqual([item.link for item in second], ["https://example.com/c"])

        third = store.filter_new("top", items, 3)
        self.assertEqual(third, [])

        try:
            store_path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    unittest.main()
