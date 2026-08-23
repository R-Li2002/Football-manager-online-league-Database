from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import Match, Player, PlayerSuspensionRecord, PlayerSuspensionServedMatch, SiteNote, Team
from schemas_read import (
    SuspensionPlayerResponse,
    SuspensionProgressResponse,
    SuspensionsResponse,
    SuspensionTeamResponse,
)
from schemas_write import SuspensionRecordUpdateRequest
from services.admin_common import LogWriter, require_admin

LEAGUE_LEVELS = ["超级", "甲级", "乙级"]
PLAYED_MATCH_STATUSES = {"played", "home_forfeit", "away_forfeit", "double_forfeit"}
SUSPENSION_NOTE_PREFIX = "competition.suspensions"
SUSPENSION_TEAM_NOTE_PREFIX = f"{SUSPENSION_NOTE_PREFIX}.team"
MAX_YELLOW_CARDS_PER_ENTRY = 3


def _record_response(
    record: PlayerSuspensionRecord,
    *,
    served_match_ids: set[int] | None = None,
    affected_matches: list[Match] | None = None,
) -> SuspensionPlayerResponse:
    total_matches = max(1, int(record.suspension_matches or 1))
    served_count = min(total_matches, len(served_match_ids or set()))
    remaining_matches = max(0, total_matches - served_count) if _is_suspended(record) else 0
    suspension_active = _is_suspended(record) and remaining_matches > 0
    affected = (affected_matches or [])[:remaining_matches] if suspension_active else []
    return SuspensionPlayerResponse(
        player_uid=record.player_uid,
        player_name=record.player_name,
        team_id=record.team_id,
        team_name=record.team_name,
        level=record.level,
        yellow_cards=int(record.yellow_cards or 0),
        yellow_card_suspended=bool(record.yellow_card_suspended) and suspension_active,
        red_card_suspended=bool(record.red_card_suspended) and suspension_active,
        red_injury_suspended=bool(record.red_injury_suspended) and suspension_active,
        suspension_matches=total_matches,
        suspension_active=suspension_active,
        suspension_served_matches=served_count,
        suspension_remaining_matches=remaining_matches,
        suspension_affected_match_ids=[int(match.id) for match in affected],
        suspension_affected_rounds=[int(match.round_no) for match in affected],
        notes=record.notes,
        updated_at=record.updated_at,
    )


def _is_suspended(record: PlayerSuspensionRecord) -> bool:
    return bool(record.yellow_card_suspended) or bool(record.red_card_suspended) or bool(record.red_injury_suspended)


def _is_completed_match(match: Match) -> bool:
    return bool(
        match.status in PLAYED_MATCH_STATUSES
        and match.home_score is not None
        and match.away_score is not None
    )


def _completed_serving_rows(
    db: Session,
    suspension_record_ids: list[int],
) -> list[PlayerSuspensionServedMatch]:
    if not suspension_record_ids:
        return []
    return (
        db.query(PlayerSuspensionServedMatch)
        .join(Match, Match.id == PlayerSuspensionServedMatch.match_id)
        .filter(
            PlayerSuspensionServedMatch.suspension_record_id.in_(suspension_record_ids),
            Match.status.in_(PLAYED_MATCH_STATUSES),
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
        )
        .all()
    )


def _team_sort_key(team: Team) -> tuple[int, str]:
    return (LEAGUE_LEVELS.index(team.level) if team.level in LEAGUE_LEVELS else 99, str(team.name or ""))


def _match_belongs_to_team(match: Match, team: Team) -> bool:
    return bool(
        match.home_team_id == team.id
        or match.away_team_id == team.id
        or match.home_team_name == team.name
        or match.away_team_name == team.name
    )


def _format_round_list(rounds: list[int]) -> str:
    return "、".join(str(round_no) for round_no in rounds)


def _build_suspension_progress(
    team: Team,
    matches: list[Match],
    team_note: SiteNote | None,
    level_note: SiteNote | None,
) -> SuspensionProgressResponse:
    marker = team_note or level_note
    checked_round = int(marker.round_no) if marker and marker.round_no is not None else None
    team_matches = [match for match in matches if match.level == team.level and _match_belongs_to_team(match, team)]
    completed_rounds = {
        int(match.round_no)
        for match in team_matches
        if match.status in PLAYED_MATCH_STATUSES
        and match.home_score is not None
        and match.away_score is not None
    }
    cancelled_rounds = {int(match.round_no) for match in team_matches if match.status == "cancelled"}
    resolved_rounds = completed_rounds | cancelled_rounds
    match_latest_recorded_round = max(completed_rounds, default=0)
    match_continuous_completed_round = 0
    for round_no in range(1, match_latest_recorded_round + 1):
        if round_no not in resolved_rounds:
            break
        match_continuous_completed_round = round_no
    match_gap_rounds = [
        round_no
        for round_no in range(1, match_latest_recorded_round + 1)
        if round_no not in resolved_rounds
    ]
    match_completed_round = match_latest_recorded_round
    progress_floor_round = max(match_latest_recorded_round, checked_round or 0)
    pending_matches = [
        match
        for match in team_matches
        if match.status in {"scheduled", "postponed"}
        and (match.home_score is None or match.away_score is None)
        and (
            int(match.round_no) in match_gap_rounds
            or match.status == "postponed"
            or int(match.round_no) > progress_floor_round
        )
    ]
    pending_matches.sort(
        key=lambda match: (
            0 if int(match.round_no) in match_gap_rounds else 1 if match.status == "postponed" else 2,
            match.match_date or datetime.max,
            int(match.round_no),
            int(match.id),
        )
    )
    next_match = pending_matches[0] if pending_matches else None
    next_round = int(next_match.round_no) if next_match else None
    next_is_postponed = bool(next_match and next_match.status == "postponed")
    next_is_gap = bool(next_match and int(next_match.round_no) in match_gap_rounds)
    marker_source = "team" if team_note else "level" if level_note else None
    applies_from_round = checked_round + 1 if checked_round is not None else None

    common_fields = {
        "match_completed_round": match_completed_round,
        "match_latest_recorded_round": match_latest_recorded_round,
        "match_continuous_completed_round": match_continuous_completed_round,
        "match_gap_rounds": match_gap_rounds,
        "suspension_checked_round": checked_round,
        "applies_from_round": applies_from_round,
        "progress_floor_round": progress_floor_round,
        "next_match_id": next_match.id if next_match else None,
        "next_match_round": next_round,
        "next_match_is_postponed": next_is_postponed,
        "next_match_is_gap": next_is_gap,
        "marker_source": marker_source,
    }

    if match_gap_rounds:
        continuous_label = (
            f"连续完成至第 {match_continuous_completed_round} 轮"
            if match_continuous_completed_round > 0
            else "尚未形成连续赛果"
        )
        return SuspensionProgressResponse(
            state="gap",
            title="赛果录入存在轮次缺口",
            detail=(
                f"{continuous_label}，第 {match_latest_recorded_round} 轮已有结果；"
                f"第 {_format_round_list(match_gap_rounds)} 轮尚未确认"
            ),
            **common_fields,
        )

    if checked_round is None:
        detail = (
            f"赛果已更新至第 {match_completed_round} 轮，尚未标注伤停核对轮次"
            if match_completed_round > 0
            else "赛果与伤停均尚未形成有效轮次"
        )
        return SuspensionProgressResponse(
            state="unknown",
            title="伤停轮次待确认",
            detail=detail,
            **common_fields,
        )

    next_detail = "当前没有待进行的联赛比赛"
    if next_round is not None:
        next_detail = (
            f"下一场为延期的第 {next_round} 轮，当前伤停核对已覆盖该场"
            if next_is_postponed and next_round <= checked_round
            else f"下一有效比赛为第 {next_round} 轮"
        )

    if match_completed_round > checked_round:
        lag = match_completed_round - checked_round
        return SuspensionProgressResponse(
            state="stale",
            title=f"伤停仅核对至第 {checked_round} 轮",
            detail=f"赛果已更新至第 {match_completed_round} 轮，落后 {lag} 轮；{next_detail}",
            **common_fields,
        )

    if checked_round > match_completed_round:
        recorded_detail = (
            f"赛果仅录入至第 {match_completed_round} 轮"
            if match_completed_round > 0
            else "赛果尚未同步"
        )
        return SuspensionProgressResponse(
            state="ahead",
            title=f"伤停已提前核对至第 {checked_round} 轮",
            detail=f"{recorded_detail}；{next_detail}",
            **common_fields,
        )

    return SuspensionProgressResponse(
        state="current",
        title=checked_round > 0 and f"伤停已核对至第 {checked_round} 轮" or "已完成赛季初伤停确认",
        detail=(
            f"伤停适用于下一场第 {next_round} 轮"
            if next_round is not None and not next_is_postponed
            else next_detail
        ),
        **common_fields,
    )


def _pending_matches_for_progress(
    team: Team,
    matches: list[Match],
    progress: SuspensionProgressResponse,
) -> list[Match]:
    gap_rounds = set(progress.match_gap_rounds or [])
    pending = [
        match
        for match in matches
        if _match_belongs_to_team(match, team)
        and match.status in {"scheduled", "postponed"}
        and (match.home_score is None or match.away_score is None)
        and (
            int(match.round_no) in gap_rounds
            or match.status == "postponed"
            or int(match.round_no) > int(progress.progress_floor_round or 0)
        )
    ]
    pending.sort(
        key=lambda match: (
            0 if int(match.round_no) in gap_rounds else 1 if match.status == "postponed" else 2,
            match.match_date or datetime.max,
            int(match.round_no),
            int(match.id),
        )
    )
    return pending


def sync_suspension_serving_for_match(
    db: Session,
    match: Match,
    *,
    was_completed: bool,
) -> list[str]:
    existing_rows = (
        db.query(PlayerSuspensionServedMatch)
        .filter(PlayerSuspensionServedMatch.match_id == match.id)
        .all()
    )
    if not _is_completed_match(match):
        for row in existing_rows:
            db.delete(row)
        return []
    if was_completed:
        return []

    existing_record_ids = {int(row.suspension_record_id) for row in existing_rows}
    team_ids = {int(value) for value in (match.home_team_id, match.away_team_id) if value is not None}
    team_names = {str(value) for value in (match.home_team_name, match.away_team_name) if str(value or "").strip()}
    team_filters = [PlayerSuspensionRecord.team_name.in_(team_names)]
    if team_ids:
        team_filters.append(PlayerSuspensionRecord.team_id.in_(team_ids))
    records = (
        db.query(PlayerSuspensionRecord)
        .filter(
            PlayerSuspensionRecord.level == match.level,
            or_(*team_filters),
        )
        .all()
    )
    record_ids = [int(record.id) for record in records]
    serving_rows = _completed_serving_rows(db, record_ids)
    served_counts: dict[int, int] = {}
    for row in serving_rows:
        served_counts[int(row.suspension_record_id)] = served_counts.get(int(row.suspension_record_id), 0) + 1

    consumed: list[str] = []
    for record in records:
        record_id = int(record.id)
        if not _is_suspended(record) or record_id in existing_record_ids:
            continue
        if served_counts.get(record_id, 0) >= max(1, int(record.suspension_matches or 1)):
            continue
        db.add(
            PlayerSuspensionServedMatch(
                suspension_record_id=record_id,
                match_id=int(match.id),
                served_at=datetime.now(),
            )
        )
        consumed.append(f"{record.team_name} / {record.player_name}")
    return consumed


def get_suspensions(
    db: Session,
    *,
    team_id: int | None = None,
    level: str | None = None,
) -> SuspensionsResponse:
    team_query = db.query(Team).filter(Team.level.in_(LEAGUE_LEVELS))
    if level is not None:
        team_query = team_query.filter(Team.level == level)
    if team_id is not None:
        team_query = team_query.filter(Team.id == team_id)
    teams = team_query.all()
    teams = sorted(teams, key=_team_sort_key)
    if team_id is not None and not teams:
        raise HTTPException(status_code=404, detail="球队不存在")
    response_levels = sorted({team.level for team in teams}, key=lambda level: LEAGUE_LEVELS.index(level))
    team_ids = {team.id for team in teams}
    team_name_to_id = {team.name: team.id for team in teams}
    match_query = db.query(Match).filter(Match.level.in_(response_levels))
    if team_id is not None:
        team_names = set(team_name_to_id)
        match_query = match_query.filter(
            or_(
                Match.home_team_id.in_(team_ids),
                Match.away_team_id.in_(team_ids),
                Match.home_team_name.in_(team_names),
                Match.away_team_name.in_(team_names),
            )
        )
    matches = match_query.order_by(Match.round_no, Match.id).all()
    note_keys = [f"{SUSPENSION_NOTE_PREFIX}.{level}" for level in response_levels]
    note_keys.extend(f"{SUSPENSION_TEAM_NOTE_PREFIX}.{item.id}" for item in teams)
    note_rows = (
        db.query(SiteNote)
        .filter(SiteNote.key.in_(note_keys))
        .all()
    )
    notes_by_key = {note.key: note for note in note_rows if note.round_no is not None}
    progress_by_team = {
        team.id: _build_suspension_progress(
            team,
            matches,
            notes_by_key.get(f"{SUSPENSION_TEAM_NOTE_PREFIX}.{team.id}"),
            notes_by_key.get(f"{SUSPENSION_NOTE_PREFIX}.{team.level}"),
        )
        for team in teams
    }
    pending_matches_by_team = {
        team.id: _pending_matches_for_progress(team, matches, progress_by_team[team.id])
        for team in teams
    }

    record_query = db.query(PlayerSuspensionRecord).filter(PlayerSuspensionRecord.level.in_(response_levels))
    if team_id is not None:
        record_query = record_query.filter(
            or_(PlayerSuspensionRecord.team_id.in_(team_ids), PlayerSuspensionRecord.team_name.in_(set(team_name_to_id)))
        )
    records = record_query.order_by(PlayerSuspensionRecord.team_name, PlayerSuspensionRecord.player_name).all()
    record_ids = [int(record.id) for record in records]
    serving_rows = _completed_serving_rows(db, record_ids)
    match_by_id = {int(match.id): match for match in matches}
    served_match_ids_by_record: dict[int, set[int]] = {}
    for row in serving_rows:
        served_match = match_by_id.get(int(row.match_id))
        if served_match and _is_completed_match(served_match):
            served_match_ids_by_record.setdefault(int(row.suspension_record_id), set()).add(int(row.match_id))

    grouped: dict[int, dict[str, list[SuspensionPlayerResponse] | list[str]]] = {
        team.id: {"one_yellow": [], "two_yellows": [], "suspended": [], "notes": []} for team in teams
    }
    players_by_uid = {
        player.uid: player
        for player in db.query(Player).filter(Player.uid.in_([record.player_uid for record in records])).all()
    }
    orphaned_by_level: dict[str, dict[str, list[SuspensionPlayerResponse] | list[str]]] = {
        level: {"one_yellow": [], "two_yellows": [], "suspended": [], "notes": []} for level in response_levels
    }
    for record in records:
        team_id = record.team_id if record.team_id in team_ids else team_name_to_id.get(record.team_name)
        player = players_by_uid.get(record.player_uid)
        current_team_id = player.team_id if player else None
        current_team_name = str(player.team_name or "") if player else ""
        record_matches_current_team = bool(
            player
            and (
                (team_id and current_team_id == team_id)
                or (record.team_name and current_team_name == record.team_name)
            )
        )
        target = grouped.get(team_id) if record_matches_current_team else orphaned_by_level[record.level]
        response = _record_response(
            record,
            served_match_ids=served_match_ids_by_record.get(int(record.id), set()),
            affected_matches=pending_matches_by_team.get(team_id, []),
        )
        if response.suspension_active:
            target["suspended"].append(response)
        if int(record.yellow_cards or 0) == 2:
            target["two_yellows"].append(response)
        elif int(record.yellow_cards or 0) == 1:
            target["one_yellow"].append(response)
        if record.notes:
            target["notes"].append(f"{record.player_name}: {record.notes}")

    orphaned_teams = [
        SuspensionTeamResponse(
            team_id=-(index + 1),
            team_name="离队 / 球队不一致记录",
            manager=None,
            level=level,
            is_orphaned=True,
            one_yellow=orphaned_by_level[level]["one_yellow"],
            two_yellows=orphaned_by_level[level]["two_yellows"],
            suspended=orphaned_by_level[level]["suspended"],
            notes=orphaned_by_level[level]["notes"],
        )
        for index, level in enumerate(response_levels)
        if any(orphaned_by_level[level][key] for key in ("one_yellow", "two_yellows", "suspended"))
    ]

    return SuspensionsResponse(
        levels=response_levels,
        teams=[
            SuspensionTeamResponse(
                team_id=team.id,
                team_name=team.name,
                manager=team.manager,
                level=team.level,
                one_yellow=grouped[team.id]["one_yellow"],
                two_yellows=grouped[team.id]["two_yellows"],
                suspended=grouped[team.id]["suspended"],
                notes=grouped[team.id]["notes"],
                progress=progress_by_team[team.id],
            )
            for team in teams
        ] + orphaned_teams,
    )


def _load_player_with_team(db: Session, player_uid: int) -> tuple[Player, Team]:
    player = db.query(Player).filter(Player.uid == player_uid).first()
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")

    team = db.query(Team).filter(Team.id == player.team_id).first() if player.team_id else None
    if not team and player.team_name:
        team = db.query(Team).filter(Team.name == player.team_name).first()
    if not team or team.level not in LEAGUE_LEVELS:
        raise HTTPException(status_code=400, detail="只能维护超级、甲级、乙级球队内球员")
    return player, team


def _should_delete(request: SuspensionRecordUpdateRequest) -> bool:
    return (
        int(request.yellow_cards or 0) <= 0
        and not request.yellow_card_suspended
        and not request.red_card_suspended
        and not request.red_injury_suspended
        and not str(request.notes or "").strip()
    )


def _normalize_player_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _merge_record_notes(records: list[PlayerSuspensionRecord], incoming: str | None) -> str | None:
    notes: list[str] = []
    for value in [*(record.notes for record in records), incoming]:
        normalized = str(value or "").strip()
        if normalized and normalized not in notes:
            notes.append(normalized)
    return "；".join(notes) or None


def _matching_suspension_records(
    db: Session,
    player: Player,
    team: Team,
) -> list[PlayerSuspensionRecord]:
    normalized_name = _normalize_player_name(player.name)
    candidates = db.query(PlayerSuspensionRecord).filter(
        or_(
            PlayerSuspensionRecord.player_uid == player.uid,
            PlayerSuspensionRecord.team_id == team.id,
            PlayerSuspensionRecord.team_name == team.name,
        )
    ).all()
    return [
        record
        for record in candidates
        if record.player_uid == player.uid
        or (
            (record.team_id == team.id or record.team_name == team.name)
            and _normalize_player_name(record.player_name) == normalized_name
        )
    ]


def get_suspension_request_level(db: Session, request: SuspensionRecordUpdateRequest) -> str:
    record = db.query(PlayerSuspensionRecord).filter(PlayerSuspensionRecord.player_uid == request.player_uid).first()
    if _should_delete(request) and record and record.level in LEAGUE_LEVELS:
        return record.level
    try:
        _, team = _load_player_with_team(db, request.player_uid)
        return team.level
    except HTTPException:
        if record and record.level in LEAGUE_LEVELS:
            return record.level
        raise


def update_suspension_record(
    db: Session,
    admin: str | None,
    request: SuspensionRecordUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    if request.yellow_cards < 0 or request.yellow_cards > MAX_YELLOW_CARDS_PER_ENTRY:
        raise HTTPException(status_code=400, detail=f"本次黄牌数只能填写 0 到 {MAX_YELLOW_CARDS_PER_ENTRY}")
    if request.suspension_matches < 1 or request.suspension_matches > 99:
        raise HTTPException(status_code=400, detail="停赛场次只能填写 1 到 99")
    if request.merge_base_yellow_cards is not None and (
        request.merge_base_yellow_cards < 0 or request.merge_base_yellow_cards > 2
    ):
        raise HTTPException(status_code=400, detail="合并前额外黄牌数只能填写 0 到 2")

    record = db.query(PlayerSuspensionRecord).filter(PlayerSuspensionRecord.player_uid == request.player_uid).first()

    if _should_delete(request):
        if record:
            record_level = record.level
            record_team_name = record.team_name
            record_player_name = record.player_name
            db.delete(record)
            from services import competition_work_service
            competition_work_service.invalidate_current_round_suspension_confirmation(db, record_level)
            db.commit()
            write_to_log("伤停记录清除", f"{record_team_name} / {record_player_name}", operator)
        else:
            write_to_log("伤停记录清除", f"UID {request.player_uid} / 记录不存在", operator)
        return {"success": True, "message": "伤停记录已清除"}

    player, team = _load_player_with_team(db, request.player_uid)
    matching_records = _matching_suspension_records(db, player, team)
    record = next((item for item in matching_records if item.player_uid == player.uid), None)
    affected_levels = {item.level for item in matching_records if item.level in LEAGUE_LEVELS}
    matching_record_ids = [int(item.id) for item in matching_records]
    all_existing_serving_rows = (
        db.query(PlayerSuspensionServedMatch)
        .filter(PlayerSuspensionServedMatch.suspension_record_id.in_(matching_record_ids))
        .all()
        if matching_record_ids
        else []
    )
    existing_serving_rows = _completed_serving_rows(db, matching_record_ids)
    served_counts: dict[int, int] = {}
    for serving_row in existing_serving_rows:
        served_counts[int(serving_row.suspension_record_id)] = served_counts.get(int(serving_row.suspension_record_id), 0) + 1
    active_existing_records = [
        item
        for item in matching_records
        if _is_suspended(item)
        and served_counts.get(int(item.id), 0) < max(1, int(item.suspension_matches or 1))
    ]
    active_existing_ids = {int(item.id) for item in active_existing_records}
    preserved_served_match_ids = {
        int(serving_row.match_id)
        for serving_row in existing_serving_rows
        if int(serving_row.suspension_record_id) in active_existing_ids
    }
    preserved_started_at = min(
        (item.suspension_started_at for item in active_existing_records if item.suspension_started_at),
        default=None,
    )
    if not record:
        record = PlayerSuspensionRecord(player_uid=player.uid)
        db.add(record)

    if request.merge_existing:
        existing_yellow_cards = sum(int(item.yellow_cards or 0) for item in matching_records)
        if request.merge_base_yellow_cards is None:
            requested_total = existing_yellow_cards + int(request.yellow_cards or 0)
        else:
            requested_total = int(request.merge_base_yellow_cards) + int(request.yellow_cards or 0)
        yellow_card_suspended = (
            bool(request.yellow_card_suspended)
            or any(bool(item.yellow_card_suspended) for item in active_existing_records)
            or requested_total >= 3
        )
        yellow_cards = requested_total % 3 if requested_total >= 3 else requested_total
        red_card_suspended = bool(request.red_card_suspended) or any(bool(item.red_card_suspended) for item in active_existing_records)
        red_injury_suspended = bool(request.red_injury_suspended) or any(bool(item.red_injury_suspended) for item in active_existing_records)
        suspension_matches = max([
            int(request.suspension_matches or 1),
            *(max(1, int(item.suspension_matches or 1)) for item in active_existing_records),
        ])
        notes = _merge_record_notes(matching_records, request.notes)
    else:
        requested_total = int(request.yellow_cards or 0)
        yellow_card_suspended = bool(request.yellow_card_suspended) or requested_total >= 3
        yellow_cards = requested_total % 3 if requested_total >= 3 else requested_total
        red_card_suspended = bool(request.red_card_suspended)
        red_injury_suspended = bool(request.red_injury_suspended)
        suspension_matches = int(request.suspension_matches or 1)
        notes = str(request.notes or "").strip() or None

    suspension_enabled = bool(yellow_card_suspended or red_card_suspended or red_injury_suspended)
    preserve_existing_cycle = suspension_enabled and bool(active_existing_records)
    for serving_row in all_existing_serving_rows:
        db.delete(serving_row)
    duplicate_records = [item for item in matching_records if item is not record]
    for duplicate in duplicate_records:
        db.delete(duplicate)
    now = datetime.now()
    record.player_name = player.name
    record.team_id = team.id
    record.team_name = team.name
    record.level = team.level
    record.yellow_cards = yellow_cards
    record.yellow_card_suspended = 1 if yellow_card_suspended else 0
    record.red_card_suspended = 1 if red_card_suspended else 0
    record.red_injury_suspended = 1 if red_injury_suspended else 0
    record.suspension_matches = suspension_matches
    record.suspension_started_at = (
        preserved_started_at or now
        if suspension_enabled
        else None
    )
    record.notes = notes
    record.updated_at = now
    db.flush()
    if preserve_existing_cycle:
        for match_id in sorted(preserved_served_match_ids):
            db.add(
                PlayerSuspensionServedMatch(
                    suspension_record_id=int(record.id),
                    match_id=match_id,
                    served_at=now,
                )
            )
    from services import competition_work_service
    affected_levels.add(team.level)
    for level in affected_levels:
        competition_work_service.invalidate_current_round_suspension_confirmation(db, level)
    db.commit()
    merged = (bool(matching_records) and request.merge_existing) or bool(duplicate_records)
    message = "伤停记录已保存"
    if request.merge_existing and matching_records:
        status_parts = []
        if yellow_card_suspended:
            status_parts.append("3黄停赛")
        if yellow_cards:
            status_parts.append(f"额外 {yellow_cards} 张黄牌")
        message = f"同名记录已合并，当前为{'，'.join(status_parts) or '无黄牌记录'}"
    elif duplicate_records:
        message = "同名记录已合并并保存"
    write_to_log("伤停记录更新", f"{team.name} / {player.name}", operator)
    team_payload = get_suspensions(db, team_id=team.id)
    saved_response = None
    for team_item in team_payload.teams:
        for group_name in ("one_yellow", "two_yellows", "suspended"):
            saved_response = next(
                (item for item in getattr(team_item, group_name) if int(item.player_uid) == int(player.uid)),
                saved_response,
            )
    if saved_response is None:
        saved_response = _record_response(record)
    return {
        "success": True,
        "message": message,
        "record": saved_response.model_dump(mode="json"),
        "merged": merged,
        "merged_record_count": len(matching_records),
    }
