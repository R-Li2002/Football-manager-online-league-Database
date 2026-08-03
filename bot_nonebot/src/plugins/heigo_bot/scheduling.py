from __future__ import annotations

from datetime import datetime, time as day_time, timedelta
from typing import Any, Awaitable, Callable


DAILY_REPORT_BROADCAST_JOB = "heigo_daily_report_broadcast"
DAILY_REPORT_REFRESH_JOB = "heigo_daily_report_refresh"


def next_run_at(hour: int, now: datetime) -> datetime:
    target = datetime.combine(now.date(), day_time(hour=hour), tzinfo=now.tzinfo)
    if target <= now:
        target += timedelta(days=1)
    return target


def scheduled_targets(
    now: datetime,
    *,
    news_daily_hour: int,
    news_headline_hours: tuple[int, ...],
    include_daily_report: bool,
    daily_report_broadcast_hour: int,
    daily_report_refresh_hour: int,
) -> list[tuple[datetime, str]]:
    targets = [(next_run_at(news_daily_hour, now), "football_daily")]
    targets.extend((next_run_at(hour, now), "football_news") for hour in news_headline_hours)
    if include_daily_report:
        targets.extend((
            (next_run_at(daily_report_broadcast_hour, now), DAILY_REPORT_BROADCAST_JOB),
            (next_run_at(daily_report_refresh_hour, now), DAILY_REPORT_REFRESH_JOB),
        ))
    return targets


def daily_report_date_for_job(job_type: str, now: datetime) -> str:
    if job_type == DAILY_REPORT_BROADCAST_JOB:
        return (now.date() - timedelta(days=1)).isoformat()
    if job_type == DAILY_REPORT_REFRESH_JOB:
        return now.date().isoformat()
    raise ValueError(f"unsupported daily report job: {job_type}")


async def execute_daily_report_job(
    job_type: str,
    now: datetime,
    *,
    get_report: Callable[[str], Awaitable[dict[str, Any]]],
    warm_image: Callable[[str, str], Awaitable[Any]],
    broadcast: Callable[[dict[str, Any], str], Awaitable[Any]],
) -> dict[str, Any]:
    report_date = daily_report_date_for_job(job_type, now)
    report = await get_report(report_date)
    fingerprint = str(report.get("fingerprint") or "").strip()
    if job_type == DAILY_REPORT_REFRESH_JOB:
        await warm_image(report_date, fingerprint)
    else:
        await broadcast(report, report_date)
    return report
