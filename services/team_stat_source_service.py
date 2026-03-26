from __future__ import annotations

from sqlalchemy.orm import Session

from schemas_read import TeamStatRefreshStateResponse, TeamStatSourcesResponse
from services.league_service import (
    REALTIME_TEAM_STAT_SCOPES,
    TEAM_CACHE_REFRESH_MODE_FULL_RECALC,
    TEAM_CACHE_REFRESH_MODE_TARGETED_RECALC,
    TEAM_CACHE_REFRESH_MODE_UNKNOWN,
    TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL,
    collect_team_stat_overlays,
)

TEAM_CACHED_STAT_FIELDS = ["wage", "team_size", "gk_count", "final_wage", "count_8m", "count_7m", "count_fake"]
TEAM_REALTIME_STAT_FIELDS = ["total_value", "avg_value", "avg_ca", "avg_pa", "total_growth"]
TEAM_CACHE_REFRESH_LABELS = {
    TEAM_CACHE_REFRESH_MODE_UNKNOWN: "历史缓存状态未记录",
    TEAM_CACHE_REFRESH_MODE_FULL_RECALC: "全量重算",
    TEAM_CACHE_REFRESH_MODE_TARGETED_RECALC: "定向重算",
    TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL: "写操作增量刷新",
}


def _parse_refresh_scopes(raw_scopes: str | None) -> list[str]:
    return [scope for scope in (raw_scopes or "").split(",") if scope]


def build_team_stat_refresh_state(team) -> TeamStatRefreshStateResponse:
    refresh_mode = team.stats_cache_refresh_mode or TEAM_CACHE_REFRESH_MODE_UNKNOWN
    if refresh_mode not in TEAM_CACHE_REFRESH_LABELS:
        refresh_mode = TEAM_CACHE_REFRESH_MODE_UNKNOWN

    refresh_scopes = _parse_refresh_scopes(team.stats_cache_refresh_scopes)
    refresh_label = TEAM_CACHE_REFRESH_LABELS.get(refresh_mode, TEAM_CACHE_REFRESH_LABELS[TEAM_CACHE_REFRESH_MODE_UNKNOWN])
    scope_label = "、".join(refresh_scopes) if refresh_scopes else "未记录范围"
    if team.stats_cache_refresh_at:
        summary = f"{refresh_label} @ {team.stats_cache_refresh_at.isoformat()} ({scope_label})"
    else:
        summary = f"{refresh_label} ({scope_label})"

    return TeamStatRefreshStateResponse(
        cached_read_mode="cache_hit",
        realtime_read_mode="realtime_overlay",
        last_cache_refresh_mode=refresh_mode,
        cached_read_label="缓存命中",
        realtime_read_label="实时覆盖",
        last_cache_refresh_label=refresh_label,
        last_cache_refresh_summary=summary,
        last_cache_refresh_at=team.stats_cache_refresh_at,
        last_cache_refresh_scopes=refresh_scopes,
    )


def build_team_stat_sources(team) -> TeamStatSourcesResponse:
    return TeamStatSourcesResponse(
        cached_fields=TEAM_CACHED_STAT_FIELDS,
        realtime_fields=TEAM_REALTIME_STAT_FIELDS,
        field_modes={
            **{field_name: "cached" for field_name in TEAM_CACHED_STAT_FIELDS},
            **{field_name: "realtime" for field_name in TEAM_REALTIME_STAT_FIELDS},
        },
        refresh_state=build_team_stat_refresh_state(team),
    )


def load_team_stat_overlays(db: Session, teams) -> dict[int, dict[str, float | int]]:
    return collect_team_stat_overlays(db, teams, stat_scopes=REALTIME_TEAM_STAT_SCOPES)
