from __future__ import annotations

from datetime import datetime
from threading import Lock
import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from models import CupMatch, Match, Player, Team
from schemas_read import (
    MatchPreviewAvailabilityResponse,
    MatchPreviewFixtureResponse,
    MatchPreviewHeadToHeadResponse,
    MatchPreviewPlayerResponse,
    MatchPreviewPredictionResponse,
    MatchPreviewResponse,
    MatchPreviewTeamResponse,
)
from services import (
    cup_service,
    player_power_ranking_service,
    player_ranking_service,
    read_service,
    standings_prediction_service,
    suspension_service,
    team_lineup_service,
)


PREVIEW_CACHE_TTL_SECONDS = 90
_CACHE_LOCK = Lock()
_PREVIEW_CACHE: dict[tuple[int, str, int], tuple[float, MatchPreviewResponse]] = {}


def _cache_get(db: Session, fixture_type: str, match_id: int) -> MatchPreviewResponse | None:
    key = (id(db.get_bind()), fixture_type, match_id)
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _PREVIEW_CACHE.get(key)
        if not cached:
            return None
        created_at, value = cached
        if now - created_at > PREVIEW_CACHE_TTL_SECONDS:
            _PREVIEW_CACHE.pop(key, None)
            return None
        return value.model_copy(deep=True)


def _cache_set(db: Session, fixture_type: str, match_id: int, value: MatchPreviewResponse) -> None:
    key = (id(db.get_bind()), fixture_type, match_id)
    with _CACHE_LOCK:
        if len(_PREVIEW_CACHE) >= 32:
            oldest_key = min(_PREVIEW_CACHE, key=lambda item: _PREVIEW_CACHE[item][0])
            _PREVIEW_CACHE.pop(oldest_key, None)
        _PREVIEW_CACHE[key] = (time.monotonic(), value.model_copy(deep=True))


def _stage_label(competition: str, stage: str) -> str:
    if stage == cup_service.WUMINGJIAN_QUALIFYING_STAGE:
        return cup_service.WUMINGJIAN_QUALIFYING_LABEL
    labels = {key: label for key, label, _count in cup_service.get_cup_stages(competition)}
    return labels.get(stage, stage)


def _load_fixture(db: Session, fixture_type: str, match_id: int) -> tuple[dict[str, Any], Team, Team]:
    normalized_type = str(fixture_type or "").strip().lower()
    if normalized_type == "league":
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="联赛比赛不存在")
        if match.status not in {"scheduled", "postponed"} or match.home_score is not None or match.away_score is not None:
            raise HTTPException(status_code=400, detail="只有未进行的比赛可以查看赛前情报")
        fixture = {
            "fixture_type": "league",
            "match_id": int(match.id),
            "competition": str(match.level),
            "competition_title": f"{match.level}联赛",
            "phase": "league",
            "stage": "",
            "round_no": int(match.round_no),
            "round_label": f"第{int(match.round_no)}轮",
            "neutral_venue": False,
            "home_team_id": int(match.home_team_id or 0),
            "home_team_name": str(match.home_team_name or ""),
            "away_team_id": int(match.away_team_id or 0),
            "away_team_name": str(match.away_team_name or ""),
            "status": str(match.status),
        }
    elif normalized_type == "cup":
        match = db.query(CupMatch).filter(CupMatch.id == match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="杯赛比赛不存在")
        if match.status != "scheduled" or match.home_score is not None or match.away_score is not None:
            raise HTTPException(status_code=400, detail="只有未进行的比赛可以查看赛前情报")
        if not match.home_team_id or not match.away_team_id:
            raise HTTPException(status_code=409, detail="杯赛对阵尚未完整确定")
        is_group = str(match.stage or "").startswith("group_")
        is_qualifying = match.stage == cup_service.WUMINGJIAN_QUALIFYING_STAGE
        phase = "group" if is_group else "qualifying" if is_qualifying else "knockout"
        round_no = ((int(match.slot_no) - 1) // 3) + 1 if is_group else None
        group_name = ""
        if is_group:
            group_no = int(str(match.stage).split("_", 1)[1])
            group_name = chr(64 + group_no)
            round_label = f"{group_name}组第{round_no}轮"
        else:
            round_label = _stage_label(str(match.competition), str(match.stage))
        fixture = {
            "fixture_type": "cup",
            "match_id": int(match.id),
            "competition": str(match.competition),
            "competition_title": cup_service.CUP_DEFINITIONS[str(match.competition)]["title"],
            "phase": phase,
            "stage": str(match.stage or ""),
            "round_no": round_no,
            "round_label": round_label,
            "neutral_venue": phase == "knockout",
            "home_team_id": int(match.home_team_id),
            "home_team_name": str(match.home_team_name or ""),
            "away_team_id": int(match.away_team_id),
            "away_team_name": str(match.away_team_name or ""),
            "status": str(match.status),
            "group_name": group_name,
        }
    else:
        raise HTTPException(status_code=400, detail="比赛类型仅支持 league 或 cup")

    home = db.query(Team).filter(Team.id == fixture["home_team_id"]).first()
    away = db.query(Team).filter(Team.id == fixture["away_team_id"]).first()
    if not home or not away:
        raise HTTPException(status_code=409, detail="比赛球队与当前球队库无法完整匹配")
    return fixture, home, away


def _recent_form(db: Session, team: Team) -> dict[str, Any]:
    matches = (
        db.query(Match)
        .filter(
            Match.level == team.level,
            Match.status.in_(suspension_service.PLAYED_MATCH_STATUSES),
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
            or_(
                Match.home_team_id == team.id,
                Match.away_team_id == team.id,
                Match.home_team_name == team.name,
                Match.away_team_name == team.name,
            ),
        )
        .order_by(Match.round_no.desc(), Match.id.desc())
        .limit(5)
        .all()
    )
    form: list[str] = []
    points = goals_for = goals_against = 0
    for match in reversed(matches):
        is_home = int(match.home_team_id or 0) == int(team.id) or match.home_team_name == team.name
        own = int(match.home_score if is_home else match.away_score)
        opponent = int(match.away_score if is_home else match.home_score)
        goals_for += own
        goals_against += opponent
        if own > opponent:
            form.append("W")
            points += 3
        elif own == opponent:
            form.append("D")
            points += 1
        else:
            form.append("L")
    return {"form": form, "points": points, "goals_for": goals_for, "goals_against": goals_against}


def _absence_label(player) -> str:
    parts: list[str] = []
    if player.yellow_card_suspended:
        parts.append("3黄停赛")
    if int(player.yellow_cards or 0) > 0:
        parts.append(f"额外{int(player.yellow_cards)}黄")
    if player.red_card_suspended:
        parts.append("红牌停赛")
    if player.red_injury_suspended:
        parts.append("红伤停赛")
    if player.notes:
        parts.append(str(player.notes).strip())
    return "、".join(parts) or "停赛"


def _availability(db: Session, team: Team, fixture: dict[str, Any]) -> MatchPreviewAvailabilityResponse:
    response = suspension_service.get_suspensions(db, team_id=int(team.id))
    item = next((row for row in response.teams if int(row.team_id) == int(team.id)), None)
    if not item:
        return MatchPreviewAvailabilityResponse()
    progress = item.progress
    reliable = bool(progress and progress.state in {"current", "ahead"} and progress.suspension_checked_round is not None)
    if reliable and fixture["fixture_type"] == "league":
        reliable = bool(
            int(progress.next_match_id or 0) == int(fixture["match_id"])
            or int(progress.applies_from_round or 0) == int(fixture.get("round_no") or 0)
            or (
                fixture.get("status") == "postponed"
                and int(progress.suspension_checked_round or 0) >= int(fixture.get("round_no") or 0)
            )
        )
    missing_players = [
        MatchPreviewPlayerResponse(
            player_uid=row.player_uid,
            player_name=row.player_name,
            goals=0,
            assists=0,
            mvps=0,
            appearances=0,
            roles=["缺席"],
            is_unavailable=True,
            absence_label=_absence_label(row),
        )
        for row in item.suspended
    ]
    return MatchPreviewAvailabilityResponse(
        state=progress.state if progress else "unknown",
        title=progress.title if progress else "伤停轮次待确认",
        detail=progress.detail if progress else "暂时无法判断数据时效",
        reliable=reliable,
        checked_round=progress.suspension_checked_round if progress else None,
        applies_from_round=progress.applies_from_round if progress else None,
        missing_count=len(missing_players),
        missing_players=missing_players,
    )


def _power_payload(db: Session, teams: list[Team]) -> tuple[dict[int, Any], dict[int, dict[int, float]]]:
    summaries: dict[int, Any] = {}
    player_power: dict[int, dict[int, float]] = {int(team.id): {} for team in teams}
    try:
        response = player_power_ranking_service.get_team_power_summaries(db)
        summaries = {int(item.team_id): item for item in response.items}
        for team in teams:
            ranking = player_power_ranking_service.get_player_power_ranking(
                db,
                shape="current",
                limit="all",
                team_name=team.name,
                data_version=response.data_version,
            )
            player_power[int(team.id)] = {int(item.uid): float(item.heigo_power) for item in ranking.items}
    except Exception:
        summaries = {}
    return summaries, player_power


def _leaders(
    db: Session,
    team: Team,
    ranking_rows: list[Any],
    power_by_uid: dict[int, float],
    availability: MatchPreviewAvailabilityResponse,
) -> list[MatchPreviewPlayerResponse]:
    team_rows = [
        row for row in ranking_rows
        if int(row.team_id or 0) == int(team.id) or row.team_name == team.name
    ]
    role_candidates: list[tuple[Any, str]] = []
    for metric, label in (("goals", "队内射手"), ("assists", "助攻核心"), ("mvps", "最佳球员")):
        rows = sorted(
            [row for row in team_rows if int(getattr(row, metric, 0) or 0) > 0],
            key=lambda row: (
                -int(getattr(row, metric, 0) or 0),
                -int(row.goals or 0),
                -int(row.assists or 0),
                str(row.player_name or ""),
            ),
        )
        if rows:
            role_candidates.append((rows[0], label))
    if power_by_uid:
        strongest_uid = max(power_by_uid, key=power_by_uid.get)
        power_row = next((row for row in team_rows if int(row.player_uid or 0) == strongest_uid), None)
        if power_row is None:
            player = db.query(Player).filter(Player.uid == strongest_uid).first()
            if player:
                power_row = type("PowerLeader", (), {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "goals": 0,
                    "assists": 0,
                    "mvps": 0,
                    "appearances": 0,
                })()
        if power_row is not None:
            role_candidates.append((power_row, "战力核心"))

    merged: dict[tuple[int, str], dict[str, Any]] = {}
    for row, role in role_candidates:
        key = (int(row.player_uid or 0), str(row.player_name or ""))
        payload = merged.setdefault(key, {"row": row, "roles": []})
        if role not in payload["roles"]:
            payload["roles"].append(role)
    unavailable_by_uid = {int(row.player_uid or 0): row for row in availability.missing_players if row.player_uid}
    unavailable_by_name = {row.player_name: row for row in availability.missing_players}
    uids = [uid for uid, _name in merged if uid > 0]
    positions = {
        int(player.uid): str(player.position or "")
        for player in db.query(Player).filter(Player.uid.in_(uids)).all()
    } if uids else {}
    leaders: list[MatchPreviewPlayerResponse] = []
    for (uid, name), payload in merged.items():
        row = payload["row"]
        unavailable = unavailable_by_uid.get(uid) or unavailable_by_name.get(name)
        leaders.append(MatchPreviewPlayerResponse(
            player_uid=uid or None,
            player_name=name,
            position=positions.get(uid, ""),
            goals=int(getattr(row, "goals", 0) or 0),
            assists=int(getattr(row, "assists", 0) or 0),
            mvps=int(getattr(row, "mvps", 0) or 0),
            appearances=int(getattr(row, "appearances", 0) or 0),
            heigo_power=power_by_uid.get(uid),
            roles=payload["roles"],
            is_unavailable=unavailable is not None,
            absence_label=unavailable.absence_label if unavailable else "",
        ))
    leaders.sort(key=lambda row: (-len(row.roles), -(row.goals + row.assists + row.mvps), row.player_name))
    return leaders[:3]


def _cup_context(db: Session, fixture: dict[str, Any], team_id: int) -> tuple[int | None, int | None, str]:
    if fixture["phase"] == "group":
        stage = cup_service.get_group_stage(db, fixture["competition"])
        group = next((item for item in stage.groups if item.group_name == fixture.get("group_name")), None)
        row = next((item for item in (group.standings if group else []) if int(item.team_id) == int(team_id)), None)
        if row:
            return row.rank, row.points, row.qualification_label
        return None, None, "小组排名待确认"
    if fixture["phase"] == "qualifying":
        return None, None, "单场淘汰，胜者晋级"
    return None, None, f"{fixture['round_label']}，两回合总比分决定晋级"


def _team_response(
    db: Session,
    team: Team,
    *,
    is_home: bool,
    neutral_venue: bool,
    standing: Any | None,
    power_summary: Any | None,
    lineup: Any,
    leaders: list[MatchPreviewPlayerResponse],
    availability: MatchPreviewAvailabilityResponse,
    recent: dict[str, Any],
    cup_context: tuple[int | None, int | None, str],
) -> MatchPreviewTeamResponse:
    if neutral_venue:
        venue_label = "综合"
        venue_played = int(standing.played if standing else 0)
        venue_points = int(standing.points if standing else 0)
        venue_wins = int(standing.wins if standing else 0)
        venue_draws = int(standing.draws if standing else 0)
        venue_losses = int(standing.losses if standing else 0)
    elif is_home:
        venue_label = "主场"
        venue_played = int(standing.home_played if standing else 0)
        venue_points = int(standing.home_points if standing else 0)
        venue_wins = int(standing.home_wins if standing else 0)
        venue_draws = int(standing.home_draws if standing else 0)
        venue_losses = int(standing.home_losses if standing else 0)
    else:
        venue_label = "客场"
        venue_played = int(standing.away_played if standing else 0)
        venue_points = int(standing.away_points if standing else 0)
        venue_wins = int(standing.away_wins if standing else 0)
        venue_draws = int(standing.away_draws if standing else 0)
        venue_losses = int(standing.away_losses if standing else 0)
    competition_rank, competition_points, competition_context = cup_context
    return MatchPreviewTeamResponse(
        team_id=int(team.id),
        team_name=str(team.name),
        manager=team.manager,
        level=str(team.level),
        logo_path=team.logo_path,
        rank=int(standing.rank) if standing else None,
        points=int(standing.points if standing else 0),
        played=int(standing.played if standing else 0),
        goal_difference=int(standing.goal_difference if standing else 0),
        predicted_rank=int(standing.predicted_rank) if standing else None,
        predicted_rank_min=int(standing.predicted_rank_min) if standing else None,
        predicted_rank_max=int(standing.predicted_rank_max) if standing else None,
        champion_probability=float(standing.champion_probability if standing else 0.0),
        title_race_probability=float(standing.title_race_probability if standing else 0.0),
        promotion_probability=float(standing.promotion_probability if standing else 0.0),
        relegation_probability=float(standing.relegation_probability if standing else 0.0),
        recent_form=recent["form"],
        recent_points=recent["points"],
        recent_goals_for=recent["goals_for"],
        recent_goals_against=recent["goals_against"],
        venue_label=venue_label,
        venue_played=venue_played,
        venue_points=venue_points,
        venue_wins=venue_wins,
        venue_draws=venue_draws,
        venue_losses=venue_losses,
        roster_power=float(power_summary.roster_average) if power_summary and power_summary.roster_average is not None else None,
        lineup_power=float(power_summary.lineup_average) if power_summary and power_summary.lineup_average is not None else None,
        lineup_rank=int(power_summary.lineup_rank) if power_summary and power_summary.lineup_rank else None,
        lineup_player_count=int(power_summary.lineup_player_count) if power_summary else 0,
        formation=str(lineup.formation or "4-3-3"),
        lineup_saved=bool(lineup.is_saved),
        leaders=leaders,
        availability=availability,
        competition_rank=competition_rank,
        competition_points=competition_points,
        competition_context=competition_context,
    )


def _prediction_reasons(home: MatchPreviewTeamResponse, away: MatchPreviewTeamResponse, neutral: bool) -> list[str]:
    reasons: list[str] = []
    home_power = home.lineup_power if home.lineup_power is not None else home.roster_power
    away_power = away.lineup_power if away.lineup_power is not None else away.roster_power
    if home_power is not None and away_power is not None and abs(home_power - away_power) >= 0.75:
        stronger = home if home_power > away_power else away
        reasons.append(f"{stronger.team_name}预计阵容战力更高，差距约{abs(home_power - away_power):.2f}点。")
    if abs(home.recent_points - away.recent_points) >= 3:
        stronger = home if home.recent_points > away.recent_points else away
        reasons.append(f"{stronger.team_name}近5场状态更好，取得{stronger.recent_points}分。")
    home_ppg = home.venue_points / home.venue_played if home.venue_played else 0.0
    away_ppg = away.venue_points / away.venue_played if away.venue_played else 0.0
    if not neutral and abs(home_ppg - away_ppg) >= 0.4:
        stronger = home if home_ppg > away_ppg else away
        reasons.append(f"{stronger.team_name}对应主客场表现更稳定。")
    if home.availability.reliable and away.availability.reliable and home.availability.missing_count != away.availability.missing_count:
        healthier = home if home.availability.missing_count < away.availability.missing_count else away
        reasons.append(f"{healthier.team_name}当前阵容完整度更高。")
    if not reasons:
        reasons.append("双方主要指标接近，本场更可能由临场发挥决定。")
    return reasons[:3]


def _prediction(
    standings_rows: list[Any],
    home: MatchPreviewTeamResponse,
    away: MatchPreviewTeamResponse,
    *,
    neutral_venue: bool,
) -> MatchPreviewPredictionResponse:
    home_power = home.lineup_power if home.lineup_power is not None else home.roster_power
    away_power = away.lineup_power if away.lineup_power is not None else away.roster_power
    outcome = standings_prediction_service.predict_fixture_outcome(
        [row.model_dump() for row in standings_rows],
        home_team=home.team_name,
        away_team=away.team_name,
        neutral_venue=neutral_venue,
        home_power=home_power,
        away_power=away_power,
        home_unavailable=home.availability.missing_count if home.availability.reliable else 0,
        away_unavailable=away.availability.missing_count if away.availability.reliable else 0,
    )
    home_pct = round(outcome["home_win_probability"] * 100, 1)
    draw_pct = round(outcome["draw_probability"] * 100, 1)
    away_pct = round(max(0.0, 100.0 - home_pct - draw_pct), 1)
    difference = home_pct - away_pct
    if abs(difference) < 5:
        advantage_side = "even"
        advantage_label = "势均力敌"
    else:
        advantage_side = "home" if difference > 0 else "away"
        team_name = home.team_name if difference > 0 else away.team_name
        advantage_label = f"{team_name}{'明显占优' if abs(difference) >= 15 else '略占优势'}"
    confidence = 0.32 + min(0.28, min(home.played, away.played) * 0.035)
    if home_power is not None and away_power is not None:
        confidence += 0.14
    if home.availability.reliable and away.availability.reliable:
        confidence += 0.14
    if home.lineup_saved and away.lineup_saved:
        confidence += 0.08
    confidence = round(max(0.0, min(1.0, confidence)), 2)
    confidence_label = "高" if confidence >= 0.75 else "中等" if confidence >= 0.5 else "低"
    return MatchPreviewPredictionResponse(
        home_win_probability=home_pct,
        draw_probability=draw_pct,
        away_win_probability=away_pct,
        advantage_side=advantage_side,
        advantage_label=advantage_label,
        confidence=confidence,
        confidence_label=confidence_label,
        reasons=_prediction_reasons(home, away, neutral_venue),
        note="模型参考当前积分、主客表现、阵容战力和已确认伤停，不预测具体比分。",
    )


def _stakes(fixture: dict[str, Any], home: MatchPreviewTeamResponse, away: MatchPreviewTeamResponse, team_count: int) -> tuple[str, str]:
    if fixture["phase"] == "group":
        return "小组出线关键战", f"{home.team_name}当前第{home.competition_rank or '-'}名，{away.team_name}当前第{away.competition_rank or '-'}名。"
    if fixture["phase"] == "qualifying":
        return "单场淘汰赛", "本场直接决定晋级资格，平局时由赛事规则确认晋级队。"
    if fixture["phase"] == "knockout":
        return "杯赛晋级战", f"{fixture['round_label']}采用两回合总比分决定晋级。"
    rows = [home, away]
    if any(row.title_race_probability >= 0.3 or (row.rank or 99) <= 2 for row in rows):
        return "争冠关键战", "本场涉及当前争冠集团，赛果可能直接改变前二竞争形势。"
    if home.level != "超级" and any(row.promotion_probability >= 0.45 or (row.rank or 99) <= 5 for row in rows):
        return "升级关键战", "本场涉及升级区竞争，三分对预测排名影响较大。"
    relegation_start = max(1, team_count - 4)
    if any(row.relegation_probability >= 0.45 or (row.rank or 0) >= relegation_start for row in rows):
        return "保级关键战", "双方至少一队处于降级风险区，本场积分具有直接保级价值。"
    if home.rank and away.rank and abs(home.rank - away.rank) <= 2 and abs(home.points - away.points) <= 3:
        return "排名直接竞争", "双方排名和积分接近，本场可能带来直接名次交换。"
    return "常规联赛", "本场主要影响双方近期状态与后续预测排名。"


def _head_to_head(db: Session, home: Team, away: Team) -> list[MatchPreviewHeadToHeadResponse]:
    team_ids = {int(home.id), int(away.id)}
    league_matches = db.query(Match).filter(
        Match.status.in_(suspension_service.PLAYED_MATCH_STATUSES),
        Match.home_score.is_not(None),
        Match.away_score.is_not(None),
        or_(
            and_(Match.home_team_id == home.id, Match.away_team_id == away.id),
            and_(Match.home_team_id == away.id, Match.away_team_id == home.id),
        ),
    ).all()
    cup_matches = db.query(CupMatch).filter(
        CupMatch.status == "played",
        CupMatch.home_score.is_not(None),
        CupMatch.away_score.is_not(None),
        CupMatch.home_team_id.in_(team_ids),
        CupMatch.away_team_id.in_(team_ids),
    ).all()
    rows: list[tuple[datetime, MatchPreviewHeadToHeadResponse]] = []
    for match in league_matches:
        rows.append((match.updated_at or match.created_at or datetime.min, MatchPreviewHeadToHeadResponse(
            fixture_type="league",
            competition_title=f"{match.level}联赛",
            round_label=f"第{int(match.round_no)}轮",
            home_team_name=str(match.home_team_name),
            away_team_name=str(match.away_team_name),
            home_score=int(match.home_score),
            away_score=int(match.away_score),
        )))
    for match in cup_matches:
        round_label = (
            f"{chr(64 + int(str(match.stage).split('_', 1)[1]))}组第{((int(match.slot_no) - 1) // 3) + 1}轮"
            if str(match.stage).startswith("group_") else _stage_label(str(match.competition), str(match.stage))
        )
        rows.append((match.updated_at or match.created_at or datetime.min, MatchPreviewHeadToHeadResponse(
            fixture_type="cup",
            competition_title=cup_service.CUP_DEFINITIONS[str(match.competition)]["title"],
            round_label=round_label,
            home_team_name=str(match.home_team_name),
            away_team_name=str(match.away_team_name),
            home_score=int(match.home_score),
            away_score=int(match.away_score),
        )))
    rows.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in rows[:4]]


def get_match_preview(db: Session, fixture_type: str, match_id: int) -> MatchPreviewResponse:
    normalized_type = str(fixture_type or "").strip().lower()
    cached = _cache_get(db, normalized_type, int(match_id))
    if cached is not None:
        return cached
    fixture, home_team, away_team = _load_fixture(db, normalized_type, int(match_id))
    standings = read_service.get_standings(db)
    standing_by_id = {int(row.team_id or 0): row for row in standings.rows if row.team_id}
    power_summaries, player_power = _power_payload(db, [home_team, away_team])
    try:
        ranking_rows = player_ranking_service.get_player_rankings(db).rows
    except Exception:
        ranking_rows = []
    home_availability = _availability(db, home_team, fixture)
    away_availability = _availability(db, away_team, fixture)
    home_lineup = team_lineup_service.get_team_lineup(db, int(home_team.id))
    away_lineup = team_lineup_service.get_team_lineup(db, int(away_team.id))
    home_cup_context = _cup_context(db, fixture, int(home_team.id)) if fixture["fixture_type"] == "cup" else (None, None, "")
    away_cup_context = _cup_context(db, fixture, int(away_team.id)) if fixture["fixture_type"] == "cup" else (None, None, "")
    home_response = _team_response(
        db,
        home_team,
        is_home=True,
        neutral_venue=fixture["neutral_venue"],
        standing=standing_by_id.get(int(home_team.id)),
        power_summary=power_summaries.get(int(home_team.id)),
        lineup=home_lineup,
        leaders=_leaders(db, home_team, ranking_rows, player_power.get(int(home_team.id), {}), home_availability),
        availability=home_availability,
        recent=_recent_form(db, home_team),
        cup_context=home_cup_context,
    )
    away_response = _team_response(
        db,
        away_team,
        is_home=False,
        neutral_venue=fixture["neutral_venue"],
        standing=standing_by_id.get(int(away_team.id)),
        power_summary=power_summaries.get(int(away_team.id)),
        lineup=away_lineup,
        leaders=_leaders(db, away_team, ranking_rows, player_power.get(int(away_team.id), {}), away_availability),
        availability=away_availability,
        recent=_recent_form(db, away_team),
        cup_context=away_cup_context,
    )
    prediction = _prediction(standings.rows, home_response, away_response, neutral_venue=fixture["neutral_venue"])
    team_count = sum(1 for row in standings.rows if row.level == home_team.level)
    stakes_label, stakes_detail = _stakes(fixture, home_response, away_response, team_count)
    response = MatchPreviewResponse(
        fixture=MatchPreviewFixtureResponse(**{key: value for key, value in fixture.items() if key in MatchPreviewFixtureResponse.model_fields}),
        home=home_response,
        away=away_response,
        prediction=prediction,
        stakes_label=stakes_label,
        stakes_detail=stakes_detail,
        head_to_head=_head_to_head(db, home_team, away_team),
        generated_at=datetime.now(),
    )
    _cache_set(db, normalized_type, int(match_id), response)
    return response
