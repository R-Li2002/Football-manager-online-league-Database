from sqlalchemy.orm import Session

from league_settings import get_growth_age_limit
from repositories.player_repository import list_all_players
from repositories.team_repository import count_visible_teams, count_visible_teams_with_unknown_cache_refresh
from services.admin_common import LogWriter, require_admin
from services.league_service import PERSISTED_TEAM_STAT_SCOPES, TEAM_CACHE_REFRESH_MODE_FULL_RECALC, TEAM_CACHE_REFRESH_MODE_UNKNOWN, recalculate_team_stats
from wage_calculator import calculate_wage

VISIBLE_LEVEL = "隐藏"


def recalculate_wages(db: Session, admin: str | None, write_to_log: LogWriter):
    admin = require_admin(admin)
    growth_age_limit = get_growth_age_limit(db)
    players = list_all_players(db)
    updated_count = 0

    for player in players:
        try:
            wage_result = calculate_wage(
                initial_ca=player.initial_ca,
                current_ca=player.ca,
                pa=player.pa,
                age=player.age,
                position=player.position,
                growth_age_limit=growth_age_limit,
            )
            player.wage = wage_result["wage"]
            player.slot_type = wage_result["slot_type"]
            updated_count += 1
        except Exception as exc:
            print(f"计算球员 {player.name} 工资时出错: {exc}")

    recalculate_team_stats(db, stat_scopes=PERSISTED_TEAM_STAT_SCOPES)
    write_to_log("重新计算工资", f"重新计算了 {updated_count} 名球员的工资和球队统计", admin)
    return {
        "success": True,
        "message": f"已重新计算 {updated_count} 名球员的工资和球队统计",
        "audit_details": {
            "updated_player_count": updated_count,
            "growth_age_limit": growth_age_limit,
            "stat_scopes": sorted(PERSISTED_TEAM_STAT_SCOPES),
        },
    }


def rebuild_team_stat_caches(db: Session, admin: str | None, write_to_log: LogWriter):
    admin = require_admin(admin)
    team_count = count_visible_teams(db, VISIBLE_LEVEL)
    unknown_before = count_visible_teams_with_unknown_cache_refresh(db, VISIBLE_LEVEL, TEAM_CACHE_REFRESH_MODE_UNKNOWN)

    try:
        recalculate_team_stats(
            db,
            commit=False,
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            refresh_mode=TEAM_CACHE_REFRESH_MODE_FULL_RECALC,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    unknown_after = count_visible_teams_with_unknown_cache_refresh(db, VISIBLE_LEVEL, TEAM_CACHE_REFRESH_MODE_UNKNOWN)
    backfilled_count = max(unknown_before - unknown_after, 0)
    write_to_log(
        "球队缓存重算",
        f"安全全量重算 {team_count} 支可见球队缓存统计，并补齐 {backfilled_count} 支球队的刷新元数据",
        admin,
    )
    return {
        "success": True,
        "message": f"已安全全量重算 {team_count} 支球队缓存统计，并补齐 {backfilled_count} 支 unknown 刷新元数据",
        "audit_details": {
            "visible_team_count": team_count,
            "unknown_before": unknown_before,
            "unknown_after": unknown_after,
            "backfilled_count": backfilled_count,
            "stat_scopes": sorted(PERSISTED_TEAM_STAT_SCOPES),
        },
    }
