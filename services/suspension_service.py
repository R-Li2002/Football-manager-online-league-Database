from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Match, Player, PlayerSuspensionRecord, SiteNote, Team
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


def _record_response(record: PlayerSuspensionRecord) -> SuspensionPlayerResponse:
    return SuspensionPlayerResponse(
        player_uid=record.player_uid,
        player_name=record.player_name,
        team_id=record.team_id,
        team_name=record.team_name,
        level=record.level,
        yellow_cards=int(record.yellow_cards or 0),
        red_card_suspended=bool(record.red_card_suspended),
        red_injury_suspended=bool(record.red_injury_suspended),
        notes=record.notes,
        updated_at=record.updated_at,
    )


def _is_suspended(record: PlayerSuspensionRecord) -> bool:
    return int(record.yellow_cards or 0) >= 3 or bool(record.red_card_suspended) or bool(record.red_injury_suspended)


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


def get_suspensions(db: Session) -> SuspensionsResponse:
    teams = db.query(Team).filter(Team.level.in_(LEAGUE_LEVELS)).all()
    teams = sorted(teams, key=_team_sort_key)
    team_ids = {team.id for team in teams}
    team_name_to_id = {team.name: team.id for team in teams}
    matches = db.query(Match).filter(Match.level.in_(LEAGUE_LEVELS)).order_by(Match.round_no, Match.id).all()
    note_rows = (
        db.query(SiteNote)
        .filter(
            (SiteNote.key.in_([f"{SUSPENSION_NOTE_PREFIX}.{level}" for level in LEAGUE_LEVELS]))
            | (SiteNote.key.like(f"{SUSPENSION_TEAM_NOTE_PREFIX}.%"))
        )
        .all()
    )
    notes_by_key = {note.key: note for note in note_rows if note.round_no is not None}

    records = (
        db.query(PlayerSuspensionRecord)
        .filter(PlayerSuspensionRecord.level.in_(LEAGUE_LEVELS))
        .order_by(PlayerSuspensionRecord.team_name, PlayerSuspensionRecord.player_name)
        .all()
    )

    grouped: dict[int, dict[str, list[SuspensionPlayerResponse] | list[str]]] = {
        team.id: {"one_yellow": [], "two_yellows": [], "suspended": [], "notes": []} for team in teams
    }
    players_by_uid = {
        player.uid: player
        for player in db.query(Player).filter(Player.uid.in_([record.player_uid for record in records])).all()
    }
    orphaned_by_level: dict[str, dict[str, list[SuspensionPlayerResponse] | list[str]]] = {
        level: {"one_yellow": [], "two_yellows": [], "suspended": [], "notes": []} for level in LEAGUE_LEVELS
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
        response = _record_response(record)
        if _is_suspended(record):
            target["suspended"].append(response)
        elif int(record.yellow_cards or 0) == 2:
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
        for index, level in enumerate(LEAGUE_LEVELS)
        if any(orphaned_by_level[level][key] for key in ("one_yellow", "two_yellows", "suspended"))
    ]

    return SuspensionsResponse(
        levels=LEAGUE_LEVELS,
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
                progress=_build_suspension_progress(
                    team,
                    matches,
                    notes_by_key.get(f"{SUSPENSION_TEAM_NOTE_PREFIX}.{team.id}"),
                    notes_by_key.get(f"{SUSPENSION_NOTE_PREFIX}.{team.level}"),
                ),
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
        and not request.red_card_suspended
        and not request.red_injury_suspended
        and not str(request.notes or "").strip()
    )


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
    if request.yellow_cards < 0 or request.yellow_cards > 3:
        raise HTTPException(status_code=400, detail="黄牌数只能填写 0 到 3")

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
    if not record:
        record = PlayerSuspensionRecord(player_uid=player.uid)
        db.add(record)
    now = datetime.now()
    record.player_name = player.name
    record.team_id = team.id
    record.team_name = team.name
    record.level = team.level
    record.yellow_cards = int(request.yellow_cards or 0)
    record.red_card_suspended = 1 if request.red_card_suspended else 0
    record.red_injury_suspended = 1 if request.red_injury_suspended else 0
    record.notes = str(request.notes or "").strip() or None
    record.updated_at = now
    from services import competition_work_service
    competition_work_service.invalidate_current_round_suspension_confirmation(db, team.level)
    db.commit()
    write_to_log("伤停记录更新", f"{team.name} / {player.name}", operator)
    return {"success": True, "message": "伤停记录已保存"}
