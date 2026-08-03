import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo


BOT_PLUGIN_PARENT = Path(__file__).resolve().parent / "bot_nonebot" / "src" / "plugins"
if str(BOT_PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(BOT_PLUGIN_PARENT))

from heigo_bot.news_service import SeenNewsStore  # noqa: E402
from heigo_bot.scheduling import (  # noqa: E402
    DAILY_REPORT_BROADCAST_JOB,
    DAILY_REPORT_REFRESH_JOB,
    daily_report_date_for_job,
    execute_daily_report_job,
    scheduled_targets,
)


class DailyReportScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tz = ZoneInfo("Asia/Shanghai")

    def test_schedule_has_morning_broadcast_and_evening_refresh(self):
        now = datetime(2026, 8, 3, 9, 30, tzinfo=self.tz)
        targets = scheduled_targets(
            now,
            news_daily_hour=9,
            news_headline_hours=(12, 15, 18),
            include_daily_report=True,
            daily_report_broadcast_hour=10,
            daily_report_refresh_hour=22,
        )
        by_job = {job: target for target, job in targets}
        self.assertEqual(by_job[DAILY_REPORT_BROADCAST_JOB], datetime(2026, 8, 3, 10, 0, tzinfo=self.tz))
        self.assertEqual(by_job[DAILY_REPORT_REFRESH_JOB], datetime(2026, 8, 3, 22, 0, tzinfo=self.tz))

    def test_broadcast_uses_yesterday_across_month_and_year_boundaries(self):
        self.assertEqual(
            daily_report_date_for_job(DAILY_REPORT_BROADCAST_JOB, datetime(2026, 3, 1, 10, tzinfo=self.tz)),
            "2026-02-28",
        )
        self.assertEqual(
            daily_report_date_for_job(DAILY_REPORT_BROADCAST_JOB, datetime(2026, 1, 1, 10, tzinfo=self.tz)),
            "2025-12-31",
        )

    def test_refresh_uses_today_and_does_not_broadcast(self):
        get_report = AsyncMock(return_value={"report_date": "2026-08-03", "fingerprint": "today-fingerprint"})
        warm_image = AsyncMock()
        broadcast = AsyncMock()
        asyncio.run(execute_daily_report_job(
            DAILY_REPORT_REFRESH_JOB,
            datetime(2026, 8, 3, 22, tzinfo=self.tz),
            get_report=get_report,
            warm_image=warm_image,
            broadcast=broadcast,
        ))
        get_report.assert_awaited_once_with("2026-08-03")
        warm_image.assert_awaited_once_with("2026-08-03", "today-fingerprint")
        broadcast.assert_not_awaited()

    def test_broadcast_fetches_yesterday_without_running_refresh(self):
        report = {"report_date": "2026-08-02", "fingerprint": "yesterday-fingerprint"}
        get_report = AsyncMock(return_value=report)
        warm_image = AsyncMock()
        broadcast = AsyncMock()
        asyncio.run(execute_daily_report_job(
            DAILY_REPORT_BROADCAST_JOB,
            datetime(2026, 8, 3, 10, tzinfo=self.tz),
            get_report=get_report,
            warm_image=warm_image,
            broadcast=broadcast,
        ))
        get_report.assert_awaited_once_with("2026-08-02")
        warm_image.assert_not_awaited()
        broadcast.assert_awaited_once_with(report, "2026-08-02")

    def test_seen_marker_is_isolated_by_group_and_report_date(self):
        with TemporaryDirectory() as temp_dir:
            store = SeenNewsStore(Path(temp_dir) / "state.json")
            link = "heigo-daily:2026-08-02"
            store.mark_seen("heigo_daily_report:100", link)
            self.assertTrue(store.has_seen("heigo_daily_report:100", link))
            self.assertFalse(store.has_seen("heigo_daily_report:200", link))
            self.assertFalse(store.has_seen("heigo_daily_report:100", "heigo-daily:2026-08-03"))


if __name__ == "__main__":
    unittest.main()
