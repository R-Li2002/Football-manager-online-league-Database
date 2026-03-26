from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from domain_types import SLOT_TYPE_7M, SLOT_TYPE_8M, SLOT_TYPE_FAKE, normalize_slot_type, normalize_transfer_operation
from league_settings import get_growth_age_limit
from models import Player, Team, TransferLog
from repositories.player_repository import load_players_grouped_by_teams
from repositories.team_repository import get_team_by_name, list_visible_teams, list_visible_teams_by_ids
from wage_calculator import calculate_current_value, calculate_wage

TEAM_STAT_SCOPE_ROSTER = "roster"
TEAM_STAT_SCOPE_WAGE = "wage"
TEAM_STAT_SCOPE_VALUE = "value"
ALL_TEAM_STAT_SCOPES = frozenset({TEAM_STAT_SCOPE_ROSTER, TEAM_STAT_SCOPE_WAGE, TEAM_STAT_SCOPE_VALUE})
PERSISTED_TEAM_STAT_SCOPES = frozenset({TEAM_STAT_SCOPE_ROSTER, TEAM_STAT_SCOPE_WAGE})
REALTIME_TEAM_STAT_SCOPES = frozenset({TEAM_STAT_SCOPE_VALUE})
PERSISTED_TEAM_STAT_FIELDS = frozenset({"team_size", "gk_count", "count_8m", "count_7m", "count_fake", "wage", "final_wage"})
REALTIME_TEAM_STAT_FIELDS = frozenset({"total_value", "avg_value", "avg_ca", "avg_pa", "total_growth"})
TEAM_CACHE_REFRESH_MODE_UNKNOWN = "unknown"
TEAM_CACHE_REFRESH_MODE_FULL_RECALC = "full_recalc"
TEAM_CACHE_REFRESH_MODE_TARGETED_RECALC = "targeted_recalc"
TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL = "write_incremental"
ALL_TEAM_CACHE_REFRESH_MODES = frozenset(
    {
        TEAM_CACHE_REFRESH_MODE_UNKNOWN,
        TEAM_CACHE_REFRESH_MODE_FULL_RECALC,
        TEAM_CACHE_REFRESH_MODE_TARGETED_RECALC,
        TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL,
    }
)
PERSISTED_TEAM_STAT_SCOPE_ORDER = (TEAM_STAT_SCOPE_ROSTER, TEAM_STAT_SCOPE_WAGE)


def calculate_player_wage_payload(
    initial_ca: int,
    current_ca: int,
    pa: int,
    age: int,
    position: str,
    db: Session,
):
    return calculate_wage(
        initial_ca=initial_ca,
        current_ca=current_ca,
        pa=pa,
        age=age,
        position=position,
        growth_age_limit=get_growth_age_limit(db),
    )


def refresh_player_financials(player: Player, db: Session):
    wage_result = calculate_player_wage_payload(
        initial_ca=player.initial_ca,
        current_ca=player.ca,
        pa=player.pa,
        age=player.age,
        position=player.position,
        db=db,
    )
    player.wage = wage_result["wage"]
    player.slot_type = wage_result["slot_type"]
    return wage_result


def create_transfer_log(
    db: Session,
    *,
    player_uid: int,
    player_name: str,
    from_team: str,
    to_team: str,
    operation: str,
    operator: str,
    from_team_id: Optional[int] = None,
    to_team_id: Optional[int] = None,
    notes: str = "",
    ca_change: int = 0,
    pa_change: int = 0,
    age_change: int = 0,
):
    operation = normalize_transfer_operation(operation)

    if from_team_id is None and from_team:
        from_team_record = get_team_by_name(db, from_team)
        from_team_id = from_team_record.id if from_team_record else None
    if to_team_id is None and to_team:
        to_team_record = get_team_by_name(db, to_team)
        to_team_id = to_team_record.id if to_team_record else None

    log = TransferLog(
        player_uid=player_uid,
        player_name=player_name,
        from_team_id=from_team_id,
        from_team=from_team,
        to_team_id=to_team_id,
        to_team=to_team,
        operation=operation,
        ca_change=ca_change,
        pa_change=pa_change,
        age_change=age_change,
        operator=operator,
        created_at=datetime.now(),
        notes=notes,
    )
    db.add(log)
    return log


def calculate_team_final_wage(team: Team, players: list[Player]):
    level_wage_cap = {"超级": 9.4, "甲级": 8.9, "乙级": 8.6}
    level_min_wage = {"超级": 8.0, "甲级": 7.5, "乙级": 6.5}

    base_cap = level_wage_cap.get(team.level, 9.4)
    min_wage = level_min_wage.get(team.level, 8.0)

    extra_cap = 0.0
    if team.notes and "+0.1M" in team.notes:
        extra_cap = 0.1

    effective_cap = base_cap + extra_cap
    player_total_wage = sum(player.wage for player in players)
    extra_wage = team.extra_wage if team.extra_wage else 0.0
    total_wage = player_total_wage + extra_wage

    if total_wage < min_wage:
        final_wage = min_wage
        status = "normal"
    elif total_wage <= effective_cap:
        final_wage = total_wage
        status = "normal"
    else:
        overflow = total_wage - effective_cap
        if overflow > 0.3:
            final_wage = total_wage
            status = "auction"
        else:
            penalty_wage = overflow * 10 + player_total_wage
            final_wage = max(total_wage, penalty_wage)
            status = "penalty"

    return {
        "player_total_wage": player_total_wage,
        "extra_wage": extra_wage,
        "total_wage": total_wage,
        "final_wage": final_wage,
        "effective_cap": effective_cap,
        "status": status,
    }


def update_team_roster_stats(team: Team, players: list[Player]):
    roster_stats = calculate_team_roster_stats(players)
    for key, value in roster_stats.items():
        setattr(team, key, value)
    return roster_stats


def update_team_wage_stats(team: Team, players: list[Player]):
    wage_stats = calculate_team_wage_stats(team, players)
    team.wage = wage_stats["player_total_wage"]
    team.final_wage = wage_stats["final_wage"]
    return wage_stats


def update_team_value_stats(team: Team, players: list[Player]):
    value_stats = calculate_team_value_stats(players)
    for key, value in value_stats.items():
        setattr(team, key, value)
    return value_stats


def calculate_team_roster_stats(players: list[Player]):
    normalized_slot_types = [normalize_slot_type(player.slot_type) for player in players]
    return {
        "team_size": len(players),
        "gk_count": len([player for player in players if player.position and "GK" in player.position]),
        "count_8m": sum(slot_type == SLOT_TYPE_8M for slot_type in normalized_slot_types),
        "count_7m": sum(slot_type == SLOT_TYPE_7M for slot_type in normalized_slot_types),
        "count_fake": sum(slot_type == SLOT_TYPE_FAKE for slot_type in normalized_slot_types),
    }


def calculate_team_wage_stats(team: Team, players: list[Player]):
    return calculate_team_final_wage(team, players)


def calculate_team_value_stats(players: list[Player]):
    if players:
        total_value = sum(calculate_current_value(player.ca) for player in players)
        return {
            "total_value": total_value,
            "avg_value": total_value / len(players),
            "avg_ca": sum(player.ca for player in players) / len(players),
            "avg_pa": sum(player.pa for player in players) / len(players),
            "total_growth": sum((player.ca or 0) - (player.initial_ca if player.initial_ca is not None else (player.ca or 0)) for player in players),
        }

    return {
        "total_value": 0,
        "avg_value": 0,
        "avg_ca": 0,
        "avg_pa": 0,
        "total_growth": 0,
    }


def _normalize_team_ids(team_ids: Iterable[int | None] | None) -> set[int]:
    if team_ids is None:
        return set()
    return {int(team_id) for team_id in team_ids if team_id}


def _normalize_stat_scopes(stat_scopes: Iterable[str] | None) -> set[str]:
    if stat_scopes is None:
        return set(ALL_TEAM_STAT_SCOPES)
    normalized_scopes = {str(scope) for scope in stat_scopes}
    unsupported_scopes = normalized_scopes - ALL_TEAM_STAT_SCOPES
    if unsupported_scopes:
        raise ValueError(f"Unsupported team stat scopes: {sorted(unsupported_scopes)}")
    return normalized_scopes


def _normalize_refresh_mode(refresh_mode: str | None, affected_team_ids: Iterable[int | None] | None) -> str:
    if refresh_mode is None:
        return TEAM_CACHE_REFRESH_MODE_FULL_RECALC if affected_team_ids is None else TEAM_CACHE_REFRESH_MODE_TARGETED_RECALC

    normalized_mode = str(refresh_mode)
    if normalized_mode not in ALL_TEAM_CACHE_REFRESH_MODES:
        raise ValueError(f"Unsupported team cache refresh mode: {normalized_mode}")
    return normalized_mode


def _persisted_scope_names(stat_scopes: Iterable[str]) -> list[str]:
    normalized_scopes = set(stat_scopes)
    return [scope for scope in PERSISTED_TEAM_STAT_SCOPE_ORDER if scope in normalized_scopes]


def _record_team_cache_refresh(team: Team, *, refresh_mode: str, stat_scopes: Iterable[str], refreshed_at: datetime) -> None:
    persisted_scopes = _persisted_scope_names(stat_scopes)
    if not persisted_scopes:
        return

    team.stats_cache_refresh_mode = refresh_mode
    team.stats_cache_refresh_scopes = ",".join(persisted_scopes)
    team.stats_cache_refresh_at = refreshed_at


def _load_teams_for_stats(db: Session, affected_team_ids: set[int] | None) -> list[Team]:
    if affected_team_ids is None:
        return list_visible_teams(db, "隐藏")
    return list_visible_teams_by_ids(db, "隐藏", affected_team_ids)


def _load_players_grouped_by_team(db: Session, teams: list[Team]) -> dict[int, list[Player]]:
    return load_players_grouped_by_teams(db, teams)


def collect_team_stat_overlays(db: Session, teams: list[Team], stat_scopes: Iterable[str] | None = None) -> dict[int, dict]:
    normalized_scopes = _normalize_stat_scopes(stat_scopes)
    if not teams or not normalized_scopes:
        return {team.id: {} for team in teams}

    players_by_team_id = _load_players_grouped_by_team(db, teams)
    overlays = {}

    for team in teams:
        players = players_by_team_id.get(team.id, [])
        overlay = {}
        if TEAM_STAT_SCOPE_ROSTER in normalized_scopes:
            overlay.update(calculate_team_roster_stats(players))
        if TEAM_STAT_SCOPE_WAGE in normalized_scopes:
            wage_stats = calculate_team_wage_stats(team, players)
            overlay.update({"wage": wage_stats["player_total_wage"], "final_wage": wage_stats["final_wage"]})
        if TEAM_STAT_SCOPE_VALUE in normalized_scopes:
            overlay.update(calculate_team_value_stats(players))
        overlays[team.id] = overlay

    return overlays


def refresh_team_cached_stats(team: Team, players: list[Player], stat_scopes: Iterable[str] | None = None):
    normalized_scopes = _normalize_stat_scopes(stat_scopes)
    stats = {}

    if TEAM_STAT_SCOPE_ROSTER in normalized_scopes:
        stats[TEAM_STAT_SCOPE_ROSTER] = update_team_roster_stats(team, players)
    if TEAM_STAT_SCOPE_WAGE in normalized_scopes:
        stats[TEAM_STAT_SCOPE_WAGE] = update_team_wage_stats(team, players)
    if TEAM_STAT_SCOPE_VALUE in normalized_scopes:
        stats[TEAM_STAT_SCOPE_VALUE] = update_team_value_stats(team, players)

    return stats


def recalculate_team_stats(
    db: Session,
    commit: bool = True,
    affected_team_ids: Iterable[int | None] | None = None,
    stat_scopes: Iterable[str] | None = None,
    refresh_mode: str | None = None,
):
    # This helper recalculates ORM state first and only persists when commit=True.
    db.flush()
    normalized_team_ids = None if affected_team_ids is None else _normalize_team_ids(affected_team_ids)
    normalized_scopes = _normalize_stat_scopes(stat_scopes)
    normalized_refresh_mode = _normalize_refresh_mode(refresh_mode, affected_team_ids)
    refreshed_at = datetime.now()
    teams = _load_teams_for_stats(db, normalized_team_ids)
    players_by_team_id = _load_players_grouped_by_team(db, teams)

    for team in teams:
        players = players_by_team_id.get(team.id, [])
        refresh_team_cached_stats(team, players, stat_scopes=normalized_scopes)
        _record_team_cache_refresh(
            team,
            refresh_mode=normalized_refresh_mode,
            stat_scopes=normalized_scopes,
            refreshed_at=refreshed_at,
        )

    if commit:
        db.commit()


def persist_with_team_stats(
    db: Session,
    affected_team_ids: Iterable[int | None] | None = None,
    stat_scopes: Iterable[str] | None = None,
    refresh_mode: str = TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL,
):
    # Admin write actions should prefer this helper when a mutation and team
    # stat refresh need to share one final commit boundary.
    recalculate_team_stats(
        db,
        commit=False,
        affected_team_ids=affected_team_ids,
        stat_scopes=stat_scopes,
        refresh_mode=refresh_mode,
    )
    db.commit()
