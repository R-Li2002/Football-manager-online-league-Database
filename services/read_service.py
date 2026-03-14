from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import BOOTSTRAP_LOG_PATH
from models import Team
from repositories.attribute_repository import (
    get_player_attribute_by_uid,
    map_attribute_uid_to_primary_nationality,
    search_player_attributes_by_name,
)
from repositories.league_info_repository import list_league_info
from repositories.operation_audit_repository import get_latest_operation_audit, list_operation_audits, list_recent_operation_audits
from repositories.player_repository import get_player_by_uid, list_players_excluding_team, map_player_uid_to_team_name, search_players_by_name
from repositories.team_repository import list_visible_teams
from repositories.transfer_log_repository import list_recent_transfer_logs
from schemas_read import (
    AttributeSearchResponse,
    LogsResponse,
    OperationAuditResponse,
    PlayerResponse,
    PlayerAttributeDetailResponse,
    PlayerRadarMetricResponse,
    PositionScoreResponse,
    SchemaBootstrapStatusResponse,
    TeamStatRefreshStateResponse,
    TeamStatSourcesResponse,
    TeamResponse,
    TeamInfoResponse,
    WageDetailResponse,
)
from schemas_write import AdminImportResponse
from team_links import SEA_TEAM_NAME, get_players_by_team_name, get_sea_team, get_team_by_name, get_team_players
from services.league_service import (
    REALTIME_TEAM_STAT_SCOPES,
    TEAM_CACHE_REFRESH_MODE_FULL_RECALC,
    TEAM_CACHE_REFRESH_MODE_TARGETED_RECALC,
    TEAM_CACHE_REFRESH_MODE_UNKNOWN,
    TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL,
    calculate_player_wage_payload,
    collect_team_stat_overlays,
)
from services.operation_audit_service import export_operation_audits_csv
from services.reaction_service import build_player_reaction_summary

LEVEL_ORDER = {"超级": 1, "甲级": 2, "乙级": 3}
VISIBLE_LEVEL = "隐藏"
ATTRIBUTE_FALLBACK_TEAM = "大海"
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


def _build_refresh_state(team: Team) -> TeamStatRefreshStateResponse:
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


def build_team_stat_sources(team: Team) -> TeamStatSourcesResponse:
    return TeamStatSourcesResponse(
        cached_fields=TEAM_CACHED_STAT_FIELDS,
        realtime_fields=TEAM_REALTIME_STAT_FIELDS,
        field_modes={
            **{field_name: "cached" for field_name in TEAM_CACHED_STAT_FIELDS},
            **{field_name: "realtime" for field_name in TEAM_REALTIME_STAT_FIELDS},
        },
        refresh_state=_build_refresh_state(team),
    )


def get_league_info(db: Session):
    return list_league_info(db)


def get_teams(db: Session):
    teams = list_visible_teams(db, VISIBLE_LEVEL)
    sorted_teams = sorted(teams, key=lambda team: (LEVEL_ORDER.get(team.level, 99), team.name))
    overlays = collect_team_stat_overlays(db, sorted_teams, stat_scopes=REALTIME_TEAM_STAT_SCOPES)
    return [
        TeamResponse(
            id=team.id,
            name=team.name,
            manager=team.manager,
            level=team.level,
            wage=team.wage,
            team_size=team.team_size,
            gk_count=team.gk_count,
            final_wage=team.final_wage,
            count_8m=team.count_8m,
            count_7m=team.count_7m,
            count_fake=team.count_fake,
            total_value=overlays.get(team.id, {}).get("total_value", team.total_value),
            avg_value=overlays.get(team.id, {}).get("avg_value", team.avg_value),
            avg_ca=overlays.get(team.id, {}).get("avg_ca", team.avg_ca),
            avg_pa=overlays.get(team.id, {}).get("avg_pa", team.avg_pa),
            total_growth=overlays.get(team.id, {}).get("total_growth", team.total_growth),
            notes=team.notes,
            stat_sources=build_team_stat_sources(team),
        )
        for team in sorted_teams
    ]


def _build_player_responses(db: Session, players) -> list[PlayerResponse]:
    nationality_map = map_attribute_uid_to_primary_nationality(db, (player.uid for player in players))
    return [
        PlayerResponse(
            uid=player.uid,
            name=player.name,
            age=player.age,
            initial_ca=player.initial_ca,
            ca=player.ca,
            pa=player.pa,
            position=player.position,
            nationality=nationality_map.get(player.uid, player.nationality or ""),
            team_name=player.team_name,
            wage=player.wage,
            slot_type=player.slot_type or "",
        )
        for player in players
    ]


def get_all_players(db: Session):
    return _build_player_responses(db, list_players_excluding_team(db, SEA_TEAM_NAME))


def get_players_by_team(db: Session, team_name: str):
    return _build_player_responses(db, get_players_by_team_name(db, team_name))


def search_player(db: Session, player_name: str):
    return _build_player_responses(db, search_players_by_name(db, player_name))


def search_player_attributes(db: Session, player_name: str) -> list[AttributeSearchResponse]:
    players = search_player_attributes_by_name(db, player_name, limit=50)
    heigo_players = map_player_uid_to_team_name(db)
    return [
        AttributeSearchResponse(
            uid=player.uid,
            name=player.name,
            position=player.position,
            age=player.age,
            ca=player.ca,
            pa=player.pa,
            nationality=player.nationality,
            club=player.club,
            heigo_club=heigo_players.get(player.uid, ATTRIBUTE_FALLBACK_TEAM),
        )
        for player in players
    ]


def get_player_attribute_detail(
    db: Session,
    uid: int,
    visitor_token: str | None = None,
) -> PlayerAttributeDetailResponse | None:
    attr = get_player_attribute_by_uid(db, uid)
    if not attr:
        return None

    heigo_player = get_player_by_uid(db, uid)
    heigo_club = heigo_player.team_name if heigo_player else ATTRIBUTE_FALLBACK_TEAM
    positions = [
        ("GK", attr.pos_gk),
        ("DL", attr.pos_dl),
        ("DC", attr.pos_dc),
        ("DR", attr.pos_dr),
        ("WBL", attr.pos_wbl),
        ("WBR", attr.pos_wbr),
        ("DM", attr.pos_dm),
        ("ML", attr.pos_ml),
        ("MC", attr.pos_mc),
        ("MR", attr.pos_mr),
        ("AML", attr.pos_aml),
        ("AMC", attr.pos_amc),
        ("AMR", attr.pos_amr),
        ("ST", attr.pos_st),
    ]
    top_positions = [
        PositionScoreResponse(position=position, score=score)
        for position, score in sorted(
            [position for position in positions if position[1] > 0],
            key=lambda item: item[1],
            reverse=True,
        )[:6]
    ]
    if (attr.pos_gk or 0) >= 15:
        radar_profile = [
            PlayerRadarMetricResponse(label="拦截射门", value=attr.radar_gk_shot_stopping),
            PlayerRadarMetricResponse(label="身体", value=attr.radar_gk_physical),
            PlayerRadarMetricResponse(label="速度", value=attr.radar_gk_speed),
            PlayerRadarMetricResponse(label="精神", value=attr.radar_gk_mental),
            PlayerRadarMetricResponse(label="指挥防守", value=attr.radar_gk_command),
            PlayerRadarMetricResponse(label="意外性", value=attr.radar_gk_eccentricity),
            PlayerRadarMetricResponse(label="制空", value=attr.radar_gk_aerial),
            PlayerRadarMetricResponse(label="大脚", value=attr.radar_gk_kicking),
        ]
    else:
        radar_profile = [
            PlayerRadarMetricResponse(label="防守", value=attr.radar_defense),
            PlayerRadarMetricResponse(label="身体", value=attr.radar_physical),
            PlayerRadarMetricResponse(label="速度", value=attr.radar_speed),
            PlayerRadarMetricResponse(label="创造", value=attr.radar_creativity),
            PlayerRadarMetricResponse(label="进攻", value=attr.radar_attack),
            PlayerRadarMetricResponse(label="技术", value=attr.radar_technical),
            PlayerRadarMetricResponse(label="制空", value=attr.radar_aerial),
            PlayerRadarMetricResponse(label="精神", value=attr.radar_mental),
        ]

    return PlayerAttributeDetailResponse(
        uid=attr.uid,
        name=attr.name,
        position=attr.position,
        age=attr.age,
        ca=attr.ca,
        pa=attr.pa,
        nationality=attr.nationality,
        club=attr.club,
        heigo_club=heigo_club,
        height=attr.height,
        weight=attr.weight,
        left_foot=attr.left_foot,
        right_foot=attr.right_foot,
        radar_defense=attr.radar_defense,
        radar_physical=attr.radar_physical,
        radar_speed=attr.radar_speed,
        radar_creativity=attr.radar_creativity,
        radar_attack=attr.radar_attack,
        radar_technical=attr.radar_technical,
        radar_aerial=attr.radar_aerial,
        radar_mental=attr.radar_mental,
        birth_date=attr.birth_date,
        national_caps=attr.national_caps,
        national_goals=attr.national_goals,
        player_habits=attr.player_habits,
        corner=attr.corner,
        crossing=attr.crossing,
        dribbling=attr.dribbling,
        finishing=attr.finishing,
        first_touch=attr.first_touch,
        free_kick=attr.free_kick,
        heading=attr.heading,
        long_shots=attr.long_shots,
        long_throws=attr.long_throws,
        marking=attr.marking,
        passing=attr.passing,
        penalty=attr.penalty,
        tackling=attr.tackling,
        technique=attr.technique,
        aggression=attr.aggression,
        anticipation=attr.anticipation,
        bravery=attr.bravery,
        composure=attr.composure,
        concentration=attr.concentration,
        decisions=attr.decisions,
        determination=attr.determination,
        flair=attr.flair,
        leadership=attr.leadership,
        off_the_ball=attr.off_the_ball,
        positioning=attr.positioning,
        teamwork=attr.teamwork,
        vision=attr.vision,
        work_rate=attr.work_rate,
        acceleration=attr.acceleration,
        agility=attr.agility,
        balance=attr.balance,
        jumping=attr.jumping,
        natural_fitness=attr.natural_fitness,
        pace=attr.pace,
        stamina=attr.stamina,
        strength=attr.strength,
        consistency=attr.consistency,
        dirtiness=attr.dirtiness,
        important_matches=attr.important_matches,
        injury_proneness=attr.injury_proneness,
        versatility=attr.versatility,
        adaptability=attr.adaptability,
        ambition=attr.ambition,
        controversy=attr.controversy,
        loyalty=attr.loyalty,
        pressure=attr.pressure,
        professionalism=attr.professionalism,
        sportsmanship=attr.sportsmanship,
        temperament=attr.temperament,
        aerial_ability=attr.aerial_ability,
        command_of_area=attr.command_of_area,
        communication=attr.communication,
        eccentricity=attr.eccentricity,
        handling=attr.handling,
        kicking=attr.kicking,
        one_on_ones=attr.one_on_ones,
        reflexes=attr.reflexes,
        rushing_out=attr.rushing_out,
        tendency_to_punch=attr.tendency_to_punch,
        throwing=attr.throwing,
        pos_gk=attr.pos_gk,
        pos_dl=attr.pos_dl,
        pos_dc=attr.pos_dc,
        pos_dr=attr.pos_dr,
        pos_wbl=attr.pos_wbl,
        pos_wbr=attr.pos_wbr,
        pos_dm=attr.pos_dm,
        pos_ml=attr.pos_ml,
        pos_mc=attr.pos_mc,
        pos_mr=attr.pos_mr,
        pos_aml=attr.pos_aml,
        pos_amc=attr.pos_amc,
        pos_amr=attr.pos_amr,
        pos_st=attr.pos_st,
        top_positions=top_positions,
        radar_profile=radar_profile,
        reaction_summary=build_player_reaction_summary(db, uid, visitor_token=visitor_token),
    )


def get_sea_players(db: Session):
    sea_team = get_sea_team(db)
    if not sea_team:
        return []
    return get_team_players(db, sea_team)


def get_transfer_logs(db: Session):
    return list_recent_transfer_logs(db, limit=100)


def get_team_info(db: Session, team_name: str) -> TeamInfoResponse:
    team = get_team_by_name(db, team_name)
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在")
    return TeamInfoResponse(
        id=team.id,
        name=team.name,
        manager=team.manager,
        level=team.level,
        wage=team.wage,
        notes=team.notes,
    )


def get_player_wage_detail(db: Session, uid: int) -> WageDetailResponse:
    player = get_player_by_uid(db, uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")
    return WageDetailResponse.model_validate(
        calculate_player_wage_payload(
            initial_ca=player.initial_ca,
            current_ca=player.ca,
            pa=player.pa,
            age=player.age,
            position=player.position,
            db=db,
        )
    )


def get_recent_logs(log_file: str, limit: int = 200) -> LogsResponse:
    if not log_file:
        return LogsResponse(logs="")
    try:
        with open(log_file, "r", encoding="utf-8") as log_stream:
            content = log_stream.read()
    except FileNotFoundError:
        return LogsResponse(logs="")

    lines = content.strip().split("\n")
    recent_lines = lines[-limit:] if len(lines) > limit else lines
    return LogsResponse(logs="\n".join(recent_lines))


def get_schema_bootstrap_status(limit: int = 5) -> SchemaBootstrapStatusResponse:
    log_path = Path(BOOTSTRAP_LOG_PATH)
    if not log_path.exists():
        return SchemaBootstrapStatusResponse(
            log_path=str(log_path),
            file_exists=False,
            latest_event=None,
            recent_events=[],
        )

    with log_path.open("r", encoding="utf-8", errors="replace") as log_stream:
        lines = [line.strip() for line in log_stream.readlines() if line.strip()]

    recent_events = lines[-limit:] if len(lines) > limit else lines
    latest_event = recent_events[-1] if recent_events else None
    return SchemaBootstrapStatusResponse(
        log_path=str(log_path),
        file_exists=True,
        latest_event=latest_event,
        recent_events=recent_events,
    )


def _expand_operation_audit_details(details: dict | None) -> dict:
    if not isinstance(details, dict):
        return {}

    response_payload = details.get("response")
    if not isinstance(response_payload, dict):
        return details

    merged = dict(response_payload)
    merged.update(details)
    return merged


def _build_operation_audit_response(record) -> OperationAuditResponse:
    details = _expand_operation_audit_details(record.details)
    return OperationAuditResponse(
        id=record.id,
        category=record.category,
        action=record.action,
        operation_label=details.get("operation_label") if isinstance(details, dict) else None,
        status=record.status,
        source=record.source,
        operator=record.operator,
        summary=record.summary,
        details=details,
        created_at=record.created_at,
    )


def get_recent_operation_audits(db: Session, limit: int = 20, category: str | None = None) -> list[OperationAuditResponse]:
    return [_build_operation_audit_response(record) for record in list_recent_operation_audits(db, limit=limit, category=category)]


def get_latest_formal_import_summary(db: Session) -> dict | None:
    record = get_latest_operation_audit(db, category="import", action="formal_import", source="admin_ui")
    if not record:
        record = get_latest_operation_audit(db, category="import", action="formal_import")
    if not record:
        return None
    return _expand_operation_audit_details(record.details) or None


def get_latest_formal_import_response(db: Session) -> Optional[AdminImportResponse]:
    details = get_latest_formal_import_summary(db)
    if not details:
        return None
    return AdminImportResponse.model_validate(details)


def export_operation_audits_report(db: Session, category: str | None = None, limit: int | None = None) -> str:
    records = list_operation_audits(db, category=category, limit=limit)
    return export_operation_audits_csv(records)
