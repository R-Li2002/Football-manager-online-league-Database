from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Match, MatchPlayerEvent, OperationAudit, Player, SiteNote, Team
from repositories.attribute_repository import count_attribute_players, get_default_attribute_version
from schemas_read import DataStatusItemResponse, DataStatusResponse
from services.competition_work_service import evaluate_match_readiness
from services.site_note_service import build_suspension_note_key, build_suspension_team_note_key


LEAGUE_LEVELS = ("超级", "甲级", "乙级")
STATUS_LABELS = {
    "normal": "已同步",
    "pending": "待补录",
    "stale": "已延迟",
    "error": "需修正",
    "unknown": "待确认",
}


def _latest_audit(db: Session, action: str) -> OperationAudit | None:
    return (
        db.query(OperationAudit)
        .filter(OperationAudit.category == "import", OperationAudit.action == action, OperationAudit.status == "success")
        .order_by(OperationAudit.created_at.desc(), OperationAudit.id.desc())
        .first()
    )


def _audit_response(record: OperationAudit | None) -> dict:
    if not record:
        return {}
    details = record.details
    response = details.get("response") if isinstance(details, dict) else None
    return response if isinstance(response, dict) else {}


def _source_name(value: str | None) -> str | None:
    clean_value = str(value or "").strip()
    return Path(clean_value).name if clean_value else None


def _item(*, status: str, **kwargs) -> DataStatusItemResponse:
    return DataStatusItemResponse(status=status, status_label=STATUS_LABELS[status], **kwargs)


def _continuous_ready_round(rounds: dict[int, list[tuple[bool, bool, list[str]]]], readiness_index: int) -> int:
    completed_round = 0
    for round_no in sorted(rounds):
        if round_no != completed_round + 1:
            break
        rows = rounds[round_no]
        if not rows or not all(bool(row[readiness_index]) for row in rows):
            break
        completed_round = round_no
    return completed_round


def _build_roster_status(db: Session) -> DataStatusItemResponse:
    audit = _latest_audit(db, "formal_import")
    response = _audit_response(audit)
    team_count = db.query(func.count(Team.id)).filter(Team.level.in_(LEAGUE_LEVELS)).scalar() or 0
    player_count = (
        db.query(func.count(Player.uid))
        .join(Team, Team.id == Player.team_id)
        .filter(Team.level.in_(LEAGUE_LEVELS))
        .scalar()
        or 0
    )
    source = _source_name(response.get("workbook_path"))
    if not team_count:
        status = "unknown"
        message = "尚未导入当前联赛球队与名单"
    elif audit:
        status = "normal"
        message = f"当前联赛共 {team_count} 支球队、{player_count} 名球员"
    else:
        status = "unknown"
        message = f"已有 {team_count} 支球队、{player_count} 名球员，但未找到正式导入审计"
    return _item(
        key="roster",
        label="联赛名单",
        scope="all",
        status=status,
        completed_count=player_count,
        total_count=player_count,
        source=source,
        updated_at=audit.created_at if audit else None,
        message=message,
        target_tab="players",
    )


def _build_attribute_status(db: Session) -> DataStatusItemResponse:
    version = get_default_attribute_version(db)
    player_count = count_attribute_players(db, version)
    audit = _latest_audit(db, "attribute_import")
    response = _audit_response(audit)
    source = _source_name(response.get("attributes_csv_path"))
    status = "normal" if player_count else "unknown"
    message = f"属性版本 {version}，共 {player_count:,} 名球员" if player_count else "球员数据库尚未导入"
    return _item(
        key="attributes",
        label="球员数据库",
        scope="all",
        status=status,
        completed_count=player_count,
        total_count=player_count,
        data_version=version,
        source=source,
        updated_at=audit.created_at if audit else None,
        message=message,
        target_tab="database",
        target_subtab="search",
    )


def _match_readiness_by_level(db: Session):
    matches = (
        db.query(Match)
        .filter(Match.level.in_(LEAGUE_LEVELS))
        .order_by(Match.level, Match.round_no, Match.id)
        .all()
    )
    match_ids = [match.id for match in matches]
    events_by_match: dict[int, list[MatchPlayerEvent]] = defaultdict(list)
    if match_ids:
        for event in db.query(MatchPlayerEvent).filter(MatchPlayerEvent.match_id.in_(match_ids)).all():
            events_by_match[event.match_id].append(event)

    by_level: dict[str, dict] = {}
    for level in LEAGUE_LEVELS:
        level_matches = [match for match in matches if match.level == level]
        rounds: dict[int, list[tuple[bool, bool, list[str]]]] = defaultdict(list)
        latest_update = None
        source = None
        source_timestamp = None
        active_round = 0
        for match in level_matches:
            result_ready, event_ready, issue_codes, _messages = evaluate_match_readiness(
                match,
                events_by_match.get(match.id, []),
            )
            rounds[int(match.round_no)].append((result_ready, event_ready, issue_codes))
            if str(match.status or "scheduled") != "scheduled":
                active_round = max(active_round, int(match.round_no or 0))
            timestamps = [match.updated_at]
            timestamps.extend(event.updated_at for event in events_by_match.get(match.id, []) if event.updated_at)
            item_update = max((value for value in timestamps if value), default=None)
            if item_update and (latest_update is None or item_update > latest_update):
                latest_update = item_update
            if match.source_file and match.updated_at and (source_timestamp is None or match.updated_at > source_timestamp):
                source = _source_name(match.source_file)
                source_timestamp = match.updated_at
        by_level[level] = {
            "matches": level_matches,
            "rounds": rounds,
            "active_round": active_round,
            "latest_round": max(rounds, default=0),
            "result_round": _continuous_ready_round(rounds, 0),
            "event_round": _continuous_ready_round(rounds, 1),
            "latest_update": latest_update,
            "source": source,
        }
    return by_level


def _active_readiness_rows(info: dict) -> list[tuple[bool, bool, list[str]]]:
    active_round = int(info["active_round"] or 0)
    return [row for round_no, rows in info["rounds"].items() if round_no <= active_round for row in rows]


def _build_competition_statuses(readiness_by_level: dict[str, dict]) -> list[DataStatusItemResponse]:
    items: list[DataStatusItemResponse] = []
    for level in LEAGUE_LEVELS:
        info = readiness_by_level[level]
        active_rows = _active_readiness_rows(info)
        result_ready_count = sum(int(row[0]) for row in active_rows)
        result_pending_count = sum(int("missing_result" in row[2]) for row in active_rows)
        result_error_count = sum(
            int(any(code in {"invalid_score", "invalid_status"} for code in row[2]))
            for row in active_rows
        )
        schedule_status = "error" if result_error_count else "pending" if result_pending_count else "normal"
        if not info["matches"]:
            schedule_status = "unknown"
        if not info["active_round"] and info["matches"]:
            schedule_message = f"已导入 {info['latest_round']} 轮赛程，尚未产生赛果"
        else:
            schedule_message = f"连续完成至第 {info['result_round']} 轮"
            if result_pending_count:
                schedule_message += f"，当前进度内还有 {result_pending_count} 场待录"
            if result_error_count:
                schedule_message += f"，{result_error_count} 场数据异常"
        schedule_item = _item(
            key="schedule",
            label="赛程",
            scope=level,
            status=schedule_status,
            updated_round=info["result_round"],
            latest_round=info["latest_round"],
            completed_count=result_ready_count,
            total_count=len(active_rows),
            issue_count=result_pending_count + result_error_count,
            source=info["source"],
            updated_at=info["latest_update"],
            message=schedule_message,
            target_tab="competition",
            target_subtab="schedule",
            target_level=level,
        )
        items.append(schedule_item)
        items.append(
            _item(
                key="standings",
                label="积分榜",
                scope=level,
                status=schedule_status,
                updated_round=info["result_round"],
                latest_round=info["latest_round"],
                completed_count=result_ready_count,
                total_count=len(active_rows),
                issue_count=result_pending_count + result_error_count,
                source=info["source"],
                updated_at=info["latest_update"],
                message=f"随赛果实时计算；{schedule_message}",
                target_tab="competition",
                target_subtab="standings",
                target_level=level,
            )
        )

        event_ready_count = sum(int(row[1]) for row in active_rows)
        missing_event_count = sum(int("missing_events" in row[2]) for row in active_rows)
        event_error_count = sum(
            int(any(code.startswith("invalid_") and code not in {"invalid_score", "invalid_status"} for code in row[2]))
            for row in active_rows
        )
        event_status = "error" if event_error_count else "pending" if missing_event_count else "normal"
        if not info["matches"]:
            event_status = "unknown"
        event_message = f"球员明细连续覆盖至第 {info['event_round']} 轮"
        if missing_event_count:
            event_message += f"，还有 {missing_event_count} 场待补"
        if event_error_count:
            event_message += f"，{event_error_count} 场明细异常"
        items.append(
            _item(
                key="player_rankings",
                label="球员榜",
                scope=level,
                status=event_status,
                updated_round=info["event_round"],
                latest_round=info["latest_round"],
                completed_count=event_ready_count,
                total_count=len(active_rows),
                issue_count=missing_event_count + event_error_count,
                source=info["source"],
                updated_at=info["latest_update"],
                message=event_message,
                target_tab="competition",
                target_subtab="playerRankings",
                target_level=level,
            )
        )
    return items


def _build_suspension_statuses(db: Session, readiness_by_level: dict[str, dict]) -> list[DataStatusItemResponse]:
    teams = db.query(Team).filter(Team.level.in_(LEAGUE_LEVELS)).order_by(Team.level, Team.name).all()
    note_keys = [build_suspension_note_key(level) for level in LEAGUE_LEVELS]
    note_keys.extend(build_suspension_team_note_key(team.id) for team in teams)
    notes_by_key = {
        row.key: row
        for row in db.query(SiteNote).filter(SiteNote.key.in_(note_keys)).all()
    }
    items: list[DataStatusItemResponse] = []
    for level in LEAGUE_LEVELS:
        level_teams = [team for team in teams if team.level == level]
        level_note = notes_by_key.get(build_suspension_note_key(level))
        effective_rounds: list[int | None] = []
        updated_times = []
        for team in level_teams:
            team_note = notes_by_key.get(build_suspension_team_note_key(team.id))
            marker = team_note if team_note and team_note.round_no is not None else level_note
            effective_rounds.append(int(marker.round_no) if marker and marker.round_no is not None else None)
            if marker and marker.updated_at:
                updated_times.append(marker.updated_at)
        target_round = int(readiness_by_level[level]["result_round"] or 0)
        outdated_count = sum(int(round_no is None or round_no < target_round) for round_no in effective_rounds) if target_round else 0
        marked_rounds = [round_no for round_no in effective_rounds if round_no is not None]
        updated_round = min(marked_rounds) if marked_rounds else None
        if not level_teams:
            status = "unknown"
            message = "当前级别没有可统计球队"
        elif target_round == 0:
            status = "normal"
            message = "联赛尚未完成首轮赛果，伤停轮次等待确认"
        elif outdated_count:
            status = "stale"
            message = f"应更新至第 {target_round} 轮，仍有 {outdated_count} 支球队需要确认"
        else:
            status = "normal"
            message = f"{len(level_teams)} 支球队均已确认至第 {target_round} 轮"
        items.append(
            _item(
                key="suspensions",
                label="伤停",
                scope=level,
                status=status,
                updated_round=updated_round,
                latest_round=target_round,
                completed_count=max(0, len(level_teams) - outdated_count),
                total_count=len(level_teams),
                issue_count=outdated_count,
                updated_at=max(updated_times, default=None),
                message=message,
                target_tab="competition",
                target_subtab="suspensions",
                target_level=level,
            )
        )
    return items


def get_data_status(db: Session) -> DataStatusResponse:
    readiness_by_level = _match_readiness_by_level(db)
    items = [_build_roster_status(db), _build_attribute_status(db)]
    items.extend(_build_competition_statuses(readiness_by_level))
    items.extend(_build_suspension_statuses(db, readiness_by_level))
    return DataStatusResponse(generated_at=datetime.now(), items=items)


def get_actionable_data_statuses(db: Session, *, is_full_admin: bool, capabilities: set[str]) -> list[DataStatusItemResponse]:
    items = get_data_status(db).items
    if is_full_admin:
        return [
            item
            for item in items
            if item.key != "standings" and item.status in {"pending", "stale", "error", "unknown"}
        ]
    visible_keys = set()
    if "schedule.write" in capabilities:
        visible_keys.update({"schedule", "player_rankings"})
    if "suspensions.write" in capabilities:
        visible_keys.add("suspensions")
    return [item for item in items if item.key in visible_keys and item.status in {"pending", "stale", "error"}]
