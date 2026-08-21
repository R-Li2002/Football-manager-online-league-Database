from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import CupGroupTeam, CupMatch, Match, Team, WumingjianQualificationTeam
from repositories.team_repository import get_team_by_id, list_visible_teams
from schemas_read import (
    CupBracketResponse,
    CupGroupMatchResponse,
    CupQualifiedTeamResponse,
    CupGroupResponse,
    CupGroupSlotResponse,
    CupGroupStageResponse,
    CupGroupStandingResponse,
    CupMatchResponse,
    WumingjianQualificationResponse,
    WumingjianQualificationTeamResponse,
    TeamCupCompetitionOutlookResponse,
    TeamCupFixtureResponse,
    TeamCupOpponentProgressResponse,
    TeamCupOutlookResponse,
)
from schemas_write import CupGroupMatchResultUpdateRequest, CupGroupUpdateRequest, CupMatchResultUpdateRequest, CupMatchTeamsUpdateRequest
from services.admin_common import LogWriter, require_admin

CUP_DEFINITIONS = {
    "champions_cup": {
        "title": "冠军杯",
        "trophy_url": "/static/images/trophy/champion.png",
        "theme": "champion",
    },
    "league_cup": {
        "title": "联盟杯",
        "trophy_url": "/static/images/trophy/league.png",
        "theme": "league",
    },
    "wumingjian_cup": {
        "title": "无铭剑杯",
        "trophy_url": "/static/images/trophy/FA.png",
        "theme": "wumingjian",
    },
}

CUP_GROUP_DEFINITIONS = {
    "champions_cup": {"group_count": 5, "teams_per_group": 6},
    "league_cup": {"group_count": 4, "teams_per_group": 6},
}

CUP_STAGES_16 = [
    ("round_of_16", "1/8淘汰赛", 8),
    ("quarter_final", "1/4淘汰赛", 4),
    ("semi_final", "半决赛", 2),
    ("final", "决赛", 1),
]

CUP_STAGES_32 = [
    ("round_of_32", "1/16淘汰赛（上方主场）", 16),
    ("round_of_16", "1/8淘汰赛（下方主场）", 8),
    ("quarter_final", "1/4淘汰赛（上方主场）", 4),
    ("semi_final", "半决赛", 2),
    ("final", "决赛", 1),
]

WUMINGJIAN_QUALIFYING_STAGE = "qualifying_round"
WUMINGJIAN_QUALIFYING_LABEL = "预选赛（单场淘汰）"
WUMINGJIAN_QUALIFYING_MATCH_COUNT = 22
WUMINGJIAN_DIRECT_LIMITS = {"超级": 6, "甲级": 2, "乙级": 2}
WUMINGJIAN_EXPECTED_TEAM_COUNT = 54
WUMINGJIAN_DIRECT_TEAM_COUNT = 10
WUMINGJIAN_PRELIMINARY_TEAM_COUNT = 44

VISIBLE_LEVEL = "隐藏"
VALID_STATUSES = {"scheduled", "played"}


def get_cup_stages(competition: str) -> list[tuple[str, str, int]]:
    return CUP_STAGES_32 if competition == "wumingjian_cup" else CUP_STAGES_16


def get_first_stage(competition: str) -> str:
    return get_cup_stages(competition)[0][0]


def normalize_competition(competition: str) -> str:
    key = str(competition or "").strip()
    aliases = {
        "champion": "champions_cup",
        "champion_cup": "champions_cup",
        "champions": "champions_cup",
        "冠军杯": "champions_cup",
        "league": "league_cup",
        "联盟杯": "league_cup",
        "fa": "wumingjian_cup",
        "FA": "wumingjian_cup",
        "wumingjian": "wumingjian_cup",
        "wumingjian_cup": "wumingjian_cup",
        "无铭剑杯": "wumingjian_cup",
    }
    key = aliases.get(key, key)
    if key not in CUP_DEFINITIONS:
        raise HTTPException(status_code=404, detail="杯赛不存在")
    return key


def ensure_bracket(db: Session, competition: str) -> int:
    competition = normalize_competition(competition)
    created = 0
    stages = list(get_cup_stages(competition))
    if competition == "wumingjian_cup":
        stages.insert(0, (WUMINGJIAN_QUALIFYING_STAGE, WUMINGJIAN_QUALIFYING_LABEL, WUMINGJIAN_QUALIFYING_MATCH_COUNT))
    for stage, _label, count in stages:
        existing_slots = {
            slot
            for (slot,) in db.query(CupMatch.slot_no)
            .filter(CupMatch.competition == competition, CupMatch.stage == stage)
            .all()
        }
        for slot_no in range(1, count + 1):
            if slot_no in existing_slots:
                continue
            db.add(
                CupMatch(
                    competition=competition,
                    stage=stage,
                    slot_no=slot_no,
                    status="scheduled",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
            created += 1
    if created:
        db.commit()
    return created


def get_bracket(db: Session, competition: str) -> CupBracketResponse:
    competition = normalize_competition(competition)
    ensure_bracket(db, competition)
    matches = (
        db.query(CupMatch)
        .filter(CupMatch.competition == competition)
        .order_by(CupMatch.stage, CupMatch.slot_no)
        .all()
    )
    matches_by_stage = {(match.stage, match.slot_no): match for match in matches}
    definition = CUP_DEFINITIONS[competition]
    stages: list[dict[str, Any]] = []
    for stage, label, count in get_cup_stages(competition):
        stages.append(
            {
                "key": stage,
                "label": label,
                "matches": [_cup_match_response(matches_by_stage[(stage, slot_no)]) for slot_no in range(1, count + 1)],
            }
        )
    return CupBracketResponse(
        competition=competition,
        title=definition["title"],
        trophy_url=definition["trophy_url"],
        stages=stages,
    )


def _wumingjian_rounds_complete(db: Session) -> bool:
    for level in WUMINGJIAN_DIRECT_LIMITS:
        for round_no in (15, 16):
            matches = (
                db.query(Match)
                .filter(Match.level == level, Match.round_no == round_no)
                .all()
            )
            if not matches or any(
                match.status not in {"played", "home_forfeit", "away_forfeit", "double_forfeit"}
                or match.home_score is None
                or match.away_score is None
                for match in matches
            ):
                return False
    return True


def _current_wumingjian_qualification_teams(db: Session) -> list[dict[str, Any]]:
    from services import match_service

    standings = match_service.get_standings(db, include_predictions=False)
    rows: list[dict[str, Any]] = []
    for level, direct_limit in WUMINGJIAN_DIRECT_LIMITS.items():
        level_rows = sorted(
            [row for row in standings.rows if row.level == level],
            key=lambda row: int(row.rank),
        )
        for row in level_rows:
            rows.append({
                "team_id": int(row.team_id),
                "team_name": row.team_name,
                "manager": row.manager,
                "level": level,
                "source_rank": int(row.rank),
                "qualification_type": "direct" if int(row.rank) <= direct_limit else "preliminary",
            })
    return rows


def _stored_wumingjian_qualification_teams(db: Session) -> list[dict[str, Any]]:
    return [
        {
            "team_id": int(row.team_id),
            "team_name": row.team_name,
            "manager": row.manager,
            "level": row.level,
            "source_rank": int(row.source_rank),
            "qualification_type": row.qualification_type,
        }
        for row in (
            db.query(WumingjianQualificationTeam)
            .order_by(WumingjianQualificationTeam.level, WumingjianQualificationTeam.source_rank)
            .all()
        )
    ]


def _lock_wumingjian_qualification(db: Session) -> list[dict[str, Any]]:
    stored = _stored_wumingjian_qualification_teams(db)
    if stored:
        return stored
    if not _wumingjian_rounds_complete(db):
        raise HTTPException(status_code=400, detail="联赛第15至16轮尚未全部完赛，暂不能锁定无铭剑杯预选资格")
    rows = _current_wumingjian_qualification_teams(db)
    direct_count = sum(1 for row in rows if row["qualification_type"] == "direct")
    preliminary_count = sum(1 for row in rows if row["qualification_type"] == "preliminary")
    if len(rows) != WUMINGJIAN_EXPECTED_TEAM_COUNT or direct_count != WUMINGJIAN_DIRECT_TEAM_COUNT or preliminary_count != WUMINGJIAN_PRELIMINARY_TEAM_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"当前联赛球队结构为 {len(rows)} 支（直通 {direct_count}、预选 {preliminary_count}），不符合无铭剑杯 54 支球队赛制",
        )
    locked_at = datetime.now()
    for row in rows:
        db.add(WumingjianQualificationTeam(**row, locked_at=locked_at))
    db.flush()
    return rows


def _wumingjian_team_response(row: dict[str, Any]) -> WumingjianQualificationTeamResponse:
    return WumingjianQualificationTeamResponse(**row)


def get_wumingjian_qualification(db: Session) -> WumingjianQualificationResponse:
    ensure_bracket(db, "wumingjian_cup")
    stored_rows = _stored_wumingjian_qualification_teams(db)
    qualification_locked = bool(stored_rows)
    rows = stored_rows or _current_wumingjian_qualification_teams(db)
    direct_rows = [row for row in rows if row["qualification_type"] == "direct"]
    preliminary_rows = [row for row in rows if row["qualification_type"] == "preliminary"]
    matches = (
        db.query(CupMatch)
        .filter(CupMatch.competition == "wumingjian_cup", CupMatch.stage == WUMINGJIAN_QUALIFYING_STAGE)
        .order_by(CupMatch.slot_no)
        .all()
    )
    rows_by_team_id = {int(row["team_id"]): row for row in rows}
    winner_rows = [
        rows_by_team_id[int(match.winner_team_id)]
        for match in matches
        if match.status == "played" and match.winner_team_id and int(match.winner_team_id) in rows_by_team_id
    ]
    assigned_match_count = sum(1 for match in matches if match.home_team_id and match.away_team_id)
    played_match_count = sum(1 for match in matches if match.status == "played" and match.winner_team_id)
    return WumingjianQualificationResponse(
        league_rounds_complete=_wumingjian_rounds_complete(db),
        qualification_locked=qualification_locked,
        direct_qualifiers=[_wumingjian_team_response(row) for row in direct_rows],
        preliminary_eligible_teams=[_wumingjian_team_response(row) for row in preliminary_rows],
        preliminary_matches=[_cup_match_response(match) for match in matches],
        preliminary_winners=[_wumingjian_team_response(row) for row in winner_rows],
        assigned_match_count=assigned_match_count,
        played_match_count=played_match_count,
        round_of_32_pool_count=len(direct_rows) + len(winner_rows),
    )


def _group_definition(competition: str) -> tuple[str, dict[str, int]]:
    competition = normalize_competition(competition)
    definition = CUP_GROUP_DEFINITIONS.get(competition)
    if not definition:
        raise HTTPException(status_code=404, detail="当前杯赛未配置小组赛")
    return competition, definition


def _group_name(group_no: int) -> str:
    return chr(64 + int(group_no))


def _group_stage_key(group_no: int) -> str:
    return f"group_{int(group_no)}"


def _group_round_robin(team_rows: list[CupGroupTeam]) -> list[tuple[int, int, CupGroupTeam, CupGroupTeam]]:
    rotation = list(sorted(team_rows, key=lambda row: row.slot_no))
    if len(rotation) != 6:
        return []
    fixtures: list[tuple[int, int, CupGroupTeam, CupGroupTeam]] = []
    for pairing_round in range(1, 6):
        first_round = (pairing_round - 1) * 2 + 1
        second_round = first_round + 1
        for pairing_no in range(3):
            left = rotation[pairing_no]
            right = rotation[-(pairing_no + 1)]
            if (pairing_round + pairing_no) % 2 == 0:
                home, away = right, left
            else:
                home, away = left, right
            first_slot = (first_round - 1) * 3 + pairing_no + 1
            second_slot = (second_round - 1) * 3 + pairing_no + 1
            fixtures.append((first_round, first_slot, home, away))
            fixtures.append((second_round, second_slot, away, home))
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return sorted(fixtures, key=lambda item: item[1])


def _ensure_group_matches(db: Session, competition: str, group_no: int, assignments: list[CupGroupTeam]) -> list[CupMatch]:
    stage = _group_stage_key(group_no)
    existing = (
        db.query(CupMatch)
        .filter(CupMatch.competition == competition, CupMatch.stage == stage)
        .order_by(CupMatch.slot_no)
        .all()
    )
    fixtures = _group_round_robin(assignments)
    if not fixtures:
        if existing:
            db.query(CupMatch).filter(CupMatch.competition == competition, CupMatch.stage == stage).delete(synchronize_session=False)
            db.commit()
        return []
    expected = [
        (slot_no, home.team_id, away.team_id)
        for _round_no, slot_no, home, away in fixtures
    ]
    current = [(match.slot_no, match.home_team_id, match.away_team_id) for match in existing]
    if current == expected:
        return existing

    results_by_direction: dict[tuple[int, int], list[tuple[int | None, int | None, str]]] = {}
    for match in existing:
        if match.home_team_id and match.away_team_id:
            key = (int(match.home_team_id), int(match.away_team_id))
            results_by_direction.setdefault(key, []).append((match.home_score, match.away_score, match.status))
    for match in existing:
        db.expunge(match)
    db.query(CupMatch).filter(CupMatch.competition == competition, CupMatch.stage == stage).delete(synchronize_session=False)
    db.flush()
    created: list[CupMatch] = []
    now = datetime.now()
    for _round_no, slot_no, home, away in fixtures:
        home_score = away_score = None
        status = "scheduled"
        direct_key = (int(home.team_id), int(away.team_id))
        reverse_key = (int(away.team_id), int(home.team_id))
        direct_results = results_by_direction.get(direct_key) or []
        reverse_results = results_by_direction.get(reverse_key) or []
        if direct_results:
            home_score, away_score, status = direct_results.pop(0)
        elif reverse_results:
            old_home_score, old_away_score, status = reverse_results.pop(0)
            home_score, away_score = old_away_score, old_home_score
        match = CupMatch(
            competition=competition,
            stage=stage,
            slot_no=slot_no,
            home_team_id=home.team_id,
            home_team_name=home.team_name,
            away_team_id=away.team_id,
            away_team_name=away.team_name,
            home_score=home_score,
            away_score=away_score,
            status=status,
            created_at=now,
            updated_at=now,
        )
        db.add(match)
        created.append(match)
    db.commit()
    return created


def _group_match_response(match: CupMatch) -> CupGroupMatchResponse:
    return CupGroupMatchResponse(
        id=match.id,
        round_no=((int(match.slot_no) - 1) // 3) + 1,
        slot_no=match.slot_no,
        home_team_id=int(match.home_team_id),
        home_team_name=str(match.home_team_name or ""),
        away_team_id=int(match.away_team_id),
        away_team_name=str(match.away_team_name or ""),
        home_score=match.home_score,
        away_score=match.away_score,
        status="played" if match.status == "played" else "scheduled",
        updated_at=match.updated_at,
    )


def _group_standings(assignments: list[CupGroupTeam], matches: list[CupMatch]) -> list[CupGroupStandingResponse]:
    rows = {
        int(team.team_id): {
            "team_id": int(team.team_id),
            "team_name": team.team_name,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }
        for team in assignments
    }
    for match in matches:
        if match.status != "played" or match.home_score is None or match.away_score is None:
            continue
        home = rows.get(int(match.home_team_id or 0))
        away = rows.get(int(match.away_team_id or 0))
        if not home or not away:
            continue
        home_score = int(match.home_score)
        away_score = int(match.away_score)
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += home_score
        home["goals_against"] += away_score
        away["goals_for"] += away_score
        away["goals_against"] += home_score
        if home_score > away_score:
            home["wins"] += 1
            away["losses"] += 1
            home["points"] += 3
        elif away_score > home_score:
            away["wins"] += 1
            home["losses"] += 1
            away["points"] += 3
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1
    ranked = sorted(
        rows.values(),
        key=lambda row: (-row["points"], -(row["goals_for"] - row["goals_against"]), -row["goals_for"], row["team_name"]),
    )
    return [
        CupGroupStandingResponse(
            rank=index,
            goal_difference=row["goals_for"] - row["goals_against"],
            **row,
        )
        for index, row in enumerate(ranked, start=1)
    ]


def _standing_sort_key(row: CupGroupStandingResponse) -> tuple[int, int, int, str]:
    return (-row.points, -row.goal_difference, -row.goals_for, row.team_name)


def _qualified_team(row: CupGroupStandingResponse, competition: str, group_name: str) -> CupQualifiedTeamResponse:
    return CupQualifiedTeamResponse(
        team_id=row.team_id,
        team_name=row.team_name,
        source_competition=competition,
        group_name=group_name,
        group_rank=row.rank,
        points=row.points,
        goal_difference=row.goal_difference,
        goals_for=row.goals_for,
        wins=row.wins,
    )


def _champions_fourth_rows(db: Session) -> tuple[list[tuple[str, CupGroupStandingResponse]], bool]:
    assignments = (
        db.query(CupGroupTeam)
        .filter(CupGroupTeam.competition == "champions_cup")
        .order_by(CupGroupTeam.group_no, CupGroupTeam.slot_no)
        .all()
    )
    fourths: list[tuple[str, CupGroupStandingResponse]] = []
    complete = True
    for group_no in range(1, CUP_GROUP_DEFINITIONS["champions_cup"]["group_count"] + 1):
        group_assignments = [row for row in assignments if row.group_no == group_no]
        matches = _ensure_group_matches(db, "champions_cup", group_no, group_assignments)
        standings = _group_standings(group_assignments, matches)
        if len(matches) != 30 or sum(match.status == "played" for match in matches) != 30:
            complete = False
        if len(standings) >= 4:
            fourths.append((_group_name(group_no), standings[3]))
    fourths.sort(key=lambda item: _standing_sort_key(item[1]))
    return fourths, complete


def _apply_group_qualification(
    db: Session,
    competition: str,
    groups: list[CupGroupResponse],
) -> tuple[bool, list[CupQualifiedTeamResponse], list[CupQualifiedTeamResponse]]:
    complete = all(
        len(group.matches) == 30 and sum(match.status == "played" for match in group.matches) == 30
        for group in groups
    )
    champions_qualifiers: list[CupQualifiedTeamResponse] = []
    league_qualifiers: list[CupQualifiedTeamResponse] = []
    if competition == "champions_cup":
        fourths = sorted(
            [(group.group_name, group.standings[3]) for group in groups if len(group.standings) >= 4],
            key=lambda item: _standing_sort_key(item[1]),
        )
        best_fourth_id = fourths[0][1].team_id if fourths else None
        for group in groups:
            for row in group.standings:
                row.qualification_provisional = not complete
                prefix = "暂列" if not complete else ""
                if row.rank <= 3 or (row.rank == 4 and row.team_id == best_fourth_id):
                    row.qualification = "champions_knockout"
                    row.qualification_label = f"{prefix}冠军杯淘汰赛"
                    champions_qualifiers.append(_qualified_team(row, competition, group.group_name))
                elif row.rank == 4:
                    row.qualification = "league_knockout"
                    row.qualification_label = f"{prefix}联盟杯淘汰赛"
                    league_qualifiers.append(_qualified_team(row, competition, group.group_name))
                else:
                    row.qualification = "eliminated"
                    row.qualification_label = f"{prefix}出局" if not complete else "出局"
    elif competition == "league_cup":
        champions_fourths, champions_complete = _champions_fourth_rows(db)
        complete = complete and champions_complete
        transfer_fourths = champions_fourths[1:]
        for group in groups:
            for row in group.standings:
                row.qualification_provisional = not complete
                prefix = "暂列" if not complete else ""
                if row.rank <= 3:
                    row.qualification = "league_knockout"
                    row.qualification_label = f"{prefix}联盟杯淘汰赛"
                    league_qualifiers.append(_qualified_team(row, competition, group.group_name))
                else:
                    row.qualification = "eliminated"
                    row.qualification_label = f"{prefix}出局" if not complete else "出局"
        league_qualifiers.extend(
            _qualified_team(row, "champions_cup", group_name)
            for group_name, row in transfer_fourths
        )
    return complete, champions_qualifiers, league_qualifiers


def get_group_stage(db: Session, competition: str) -> CupGroupStageResponse:
    competition, group_definition = _group_definition(competition)
    assignments = (
        db.query(CupGroupTeam)
        .filter(CupGroupTeam.competition == competition)
        .order_by(CupGroupTeam.group_no, CupGroupTeam.slot_no)
        .all()
    )
    assignments_by_slot = {(row.group_no, row.slot_no): row for row in assignments}
    team_ids = [row.team_id for row in assignments]
    team_by_id = {
        team.id: team
        for team in db.query(Team).filter(Team.id.in_(team_ids)).all()
    } if team_ids else {}
    groups: list[CupGroupResponse] = []
    for group_no in range(1, group_definition["group_count"] + 1):
        group_assignments = [row for row in assignments if row.group_no == group_no]
        group_matches = _ensure_group_matches(db, competition, group_no, group_assignments)
        slots: list[CupGroupSlotResponse] = []
        for slot_no in range(1, group_definition["teams_per_group"] + 1):
            assignment = assignments_by_slot.get((group_no, slot_no))
            team = team_by_id.get(assignment.team_id) if assignment else None
            slots.append(
                CupGroupSlotResponse(
                    slot_no=slot_no,
                    team_id=team.id if team else None,
                    team_name=team.name if team else None,
                    manager=team.manager if team else None,
                    level=team.level if team else None,
                    logo_path=team.logo_path if team else None,
                )
            )
        groups.append(
            CupGroupResponse(
                group_no=group_no,
                group_name=_group_name(group_no),
                teams=slots,
                matches=[_group_match_response(match) for match in group_matches],
                standings=_group_standings(group_assignments, group_matches),
            )
        )
    qualification_complete, champions_qualifiers, league_qualifiers = _apply_group_qualification(db, competition, groups)
    return CupGroupStageResponse(
        competition=competition,
        title=CUP_DEFINITIONS[competition]["title"],
        group_count=group_definition["group_count"],
        teams_per_group=group_definition["teams_per_group"],
        assigned_team_count=len(assignments),
        groups=groups,
        qualification_complete=qualification_complete,
        champions_knockout_qualifiers=champions_qualifiers,
        league_knockout_qualifiers=league_qualifiers,
    )


def _team_fixture_response(
    match: CupMatch,
    team_id: int,
    *,
    stage_label: str,
    round_no: int | None = None,
) -> TeamCupFixtureResponse:
    is_home = int(match.home_team_id or 0) == int(team_id)
    opponent_team_id = match.away_team_id if is_home else match.home_team_id
    opponent_team_name = match.away_team_name if is_home else match.home_team_name
    return TeamCupFixtureResponse(
        id=int(match.id),
        stage=match.stage,
        stage_label=stage_label,
        round_no=round_no,
        opponent_team_id=int(opponent_team_id) if opponent_team_id else None,
        opponent_team_name=str(opponent_team_name or "待定"),
        is_home=is_home,
        home_team_name=str(match.home_team_name or "待定"),
        away_team_name=str(match.away_team_name or "待定"),
        home_score=match.home_score,
        away_score=match.away_score,
        status="played" if match.status == "played" else "scheduled",
    )


def _points_gap_context(prefix: str, own_points: int, boundary_points: int) -> str:
    difference = int(own_points) - int(boundary_points)
    if difference > 0:
        return f"领先{prefix} {difference} 分"
    if difference < 0:
        return f"距{prefix} {abs(difference)} 分"
    return f"与{prefix}同分，暂比较净胜球"


def _group_qualification_context(
    competition: str,
    group: CupGroupResponse,
    standing: CupGroupStandingResponse,
    all_groups: list[CupGroupResponse],
) -> str:
    rows = group.standings
    if competition == "champions_cup" and standing.rank == 4:
        fourths = sorted(
            [item.standings[3] for item in all_groups if len(item.standings) >= 4],
            key=_standing_sort_key,
        )
        position = next((index for index, row in enumerate(fourths, start=1) if row.team_id == standing.team_id), None)
        return f"五组第四第 {position} 名" if position else "正在比较五组第四顺位"
    if competition == "champions_cup":
        if standing.rank <= 3 and len(rows) >= 4:
            return _points_gap_context("第4名", standing.points, rows[3].points)
        if standing.rank >= 5 and len(rows) >= 4:
            return _points_gap_context("第4名", standing.points, rows[3].points)
    if competition == "league_cup":
        if standing.rank <= 3 and len(rows) >= 4:
            return _points_gap_context("第4名", standing.points, rows[3].points)
        if standing.rank >= 4 and len(rows) >= 3:
            return _points_gap_context("第3名", standing.points, rows[2].points)
    return ""


def _team_group_outlook(
    db: Session,
    team: Team,
    competition: str,
) -> TeamCupCompetitionOutlookResponse | None:
    stage = get_group_stage(db, competition)
    group = next(
        (
            item
            for item in stage.groups
            if any(int(slot.team_id or 0) == int(team.id) for slot in item.teams)
        ),
        None,
    )
    if not group:
        return None
    standing = next((row for row in group.standings if int(row.team_id) == int(team.id)), None)
    team_matches = [
        match
        for match in group.matches
        if int(match.home_team_id) == int(team.id) or int(match.away_team_id) == int(team.id)
    ]
    opponent_rows: dict[int, dict[str, Any]] = {}
    for match in team_matches:
        is_home = int(match.home_team_id) == int(team.id)
        opponent_id = int(match.away_team_id if is_home else match.home_team_id)
        opponent_name = match.away_team_name if is_home else match.home_team_name
        row = opponent_rows.setdefault(
            opponent_id,
            {"team_id": opponent_id, "team_name": opponent_name, "played_legs": 0, "remaining_legs": 0},
        )
        if match.status == "played":
            row["played_legs"] += 1
        else:
            row["remaining_legs"] += 1
    opponents = [
        TeamCupOpponentProgressResponse(**row)
        for row in sorted(opponent_rows.values(), key=lambda item: (item["remaining_legs"] == 0, item["team_name"]))
    ]
    upcoming = sorted(
        [match for match in team_matches if match.status != "played"],
        key=lambda match: (match.round_no, match.slot_no),
    )
    definition = CUP_DEFINITIONS[competition]
    return TeamCupCompetitionOutlookResponse(
        competition=competition,
        title=definition["title"],
        theme=definition["theme"],
        phase="group",
        group_name=group.group_name,
        rank=standing.rank if standing else None,
        played=standing.played if standing else 0,
        points=standing.points if standing else 0,
        goal_difference=standing.goal_difference if standing else 0,
        qualification=standing.qualification if standing else "pending",
        qualification_label=standing.qualification_label if standing else "待定",
        qualification_provisional=standing.qualification_provisional if standing else True,
        qualification_context=_group_qualification_context(competition, group, standing, stage.groups) if standing else "",
        remaining_match_count=len(upcoming),
        remaining_opponent_count=sum(1 for row in opponents if row.remaining_legs > 0),
        opponents=opponents,
        next_matches=[
            TeamCupFixtureResponse(
                id=match.id,
                stage=f"group_{group.group_no}",
                stage_label=f"{group.group_name}组",
                round_no=match.round_no,
                opponent_team_id=match.away_team_id if int(match.home_team_id) == int(team.id) else match.home_team_id,
                opponent_team_name=match.away_team_name if int(match.home_team_id) == int(team.id) else match.home_team_name,
                is_home=int(match.home_team_id) == int(team.id),
                home_team_name=match.home_team_name,
                away_team_name=match.away_team_name,
                home_score=match.home_score,
                away_score=match.away_score,
                status=match.status,
            )
            for match in upcoming[:4]
        ],
    )


def _team_knockout_outlook(db: Session, team: Team, competition: str) -> TeamCupCompetitionOutlookResponse | None:
    stages = get_cup_stages(competition)
    stage_labels = {stage: label for stage, label, _count in stages}
    stage_order = {stage: index for index, (stage, _label, _count) in enumerate(stages)}
    matches = (
        db.query(CupMatch)
        .filter(
            CupMatch.competition == competition,
            ~CupMatch.stage.like("group_%"),
            ((CupMatch.home_team_id == team.id) | (CupMatch.away_team_id == team.id)),
        )
        .all()
    )
    if not matches:
        return None
    matches.sort(key=lambda match: (stage_order.get(match.stage, -1), match.slot_no))
    current = matches[-1]
    scheduled = [match for match in matches if match.status != "played"]
    if current.status != "played":
        qualification = "knockout_active"
        qualification_label = stage_labels.get(current.stage, current.stage)
        qualification_context = "等待本轮比赛"
    elif int(current.winner_team_id or 0) == int(team.id):
        if current.stage == "final":
            qualification = "champion"
            qualification_label = "杯赛冠军"
            qualification_context = "已赢得决赛"
        else:
            qualification = "advanced"
            qualification_label = "已晋级下一轮"
            qualification_context = f"已通过{stage_labels.get(current.stage, current.stage)}"
    else:
        qualification = "eliminated"
        qualification_label = "已出局"
        qualification_context = f"止步{stage_labels.get(current.stage, current.stage)}"
    definition = CUP_DEFINITIONS[competition]
    opponents = []
    if current.home_team_id and current.away_team_id:
        is_home = int(current.home_team_id) == int(team.id)
        opponents.append(
            TeamCupOpponentProgressResponse(
                team_id=int(current.away_team_id if is_home else current.home_team_id),
                team_name=str(current.away_team_name if is_home else current.home_team_name),
                played_legs=1 if current.status == "played" else 0,
                remaining_legs=0 if current.status == "played" else 1,
            )
        )
    return TeamCupCompetitionOutlookResponse(
        competition=competition,
        title=definition["title"],
        theme=definition["theme"],
        phase="knockout",
        qualification=qualification,
        qualification_label=qualification_label,
        qualification_provisional=False,
        qualification_context=qualification_context,
        remaining_match_count=len(scheduled),
        remaining_opponent_count=sum(1 for row in opponents if row.remaining_legs > 0),
        opponents=opponents,
        next_matches=[
            _team_fixture_response(match, int(team.id), stage_label=stage_labels.get(match.stage, match.stage))
            for match in scheduled[:2]
        ],
    )


def get_team_cup_outlook(db: Session, team_id: int) -> TeamCupOutlookResponse:
    team = get_team_by_id(db, int(team_id))
    if not team or team.level == VISIBLE_LEVEL:
        raise HTTPException(status_code=404, detail="球队不存在")
    competitions: list[TeamCupCompetitionOutlookResponse] = []
    for competition in ("champions_cup", "league_cup", "wumingjian_cup"):
        knockout = _team_knockout_outlook(db, team, competition)
        if knockout:
            competitions.append(knockout)
            continue
        if competition in CUP_GROUP_DEFINITIONS:
            group = _team_group_outlook(db, team, competition)
            if group:
                competitions.append(group)
    return TeamCupOutlookResponse(team_id=int(team.id), team_name=team.name, competitions=competitions)


def update_cup_group(
    db: Session,
    admin: str | None,
    competition: str,
    group_no: int,
    request: CupGroupUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    competition, group_definition = _group_definition(competition)
    if group_no < 1 or group_no > group_definition["group_count"]:
        raise HTTPException(status_code=404, detail="杯赛小组不存在")
    if len(request.team_ids) != group_definition["teams_per_group"]:
        raise HTTPException(status_code=400, detail=f"每组必须提交 {group_definition['teams_per_group']} 个球队槽位")

    normalized_ids = [int(team_id) if team_id is not None else None for team_id in request.team_ids]
    selected_ids = [team_id for team_id in normalized_ids if team_id is not None]
    if len(selected_ids) != len(set(selected_ids)):
        raise HTTPException(status_code=400, detail="同一小组不能重复选择球队")

    selected_teams = [_visible_team(db, team_id) for team_id in selected_ids]
    other_assignments = (
        db.query(CupGroupTeam)
        .filter(
            CupGroupTeam.competition == competition,
            CupGroupTeam.group_no != group_no,
            CupGroupTeam.team_id.in_(selected_ids),
        )
        .all()
    ) if selected_ids else []
    if other_assignments:
        conflict = other_assignments[0]
        raise HTTPException(
            status_code=400,
            detail=f"{conflict.team_name} 已在 {_group_name(conflict.group_no)} 组，请先从原小组移除",
        )

    team_by_id = {team.id: team for team in selected_teams if team}
    db.query(CupGroupTeam).filter(
        CupGroupTeam.competition == competition,
        CupGroupTeam.group_no == group_no,
    ).delete(synchronize_session=False)
    db.flush()
    updated_at = datetime.now()
    for slot_no, team_id in enumerate(normalized_ids, start=1):
        if team_id is None:
            continue
        team = team_by_id[team_id]
        db.add(
            CupGroupTeam(
                competition=competition,
                group_no=group_no,
                slot_no=slot_no,
                team_id=team.id,
                team_name=team.name,
                created_at=updated_at,
                updated_at=updated_at,
            )
        )
    db.commit()
    title = CUP_DEFINITIONS[competition]["title"]
    write_to_log(
        "杯赛小组编辑",
        f"{title} {_group_name(group_no)} 组，保存 {len(selected_ids)}/{group_definition['teams_per_group']} 支球队",
        operator,
    )
    return {"success": True, "message": f"{title} {_group_name(group_no)} 组已保存"}


def update_cup_group_match_result(
    db: Session,
    admin: str | None,
    competition: str,
    match_id: int,
    request: CupGroupMatchResultUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    competition, _group_definition_value = _group_definition(competition)
    match = db.query(CupMatch).filter(CupMatch.id == match_id, CupMatch.competition == competition).first()
    if not match or not str(match.stage or "").startswith("group_"):
        raise HTTPException(status_code=404, detail="杯赛小组赛对阵不存在")
    home_score = request.home_score
    away_score = request.away_score
    if (home_score is None) != (away_score is None):
        raise HTTPException(status_code=400, detail="请同时填写双方比分，或同时清空")
    if home_score is not None and (home_score < 0 or home_score > 99 or away_score < 0 or away_score > 99):
        raise HTTPException(status_code=400, detail="比分只能填写 0 到 99")
    match.home_score = home_score
    match.away_score = away_score
    match.status = "played" if home_score is not None else "scheduled"
    if home_score is None or home_score == away_score:
        match.winner_team_id = None
        match.winner_team_name = None
    elif home_score > away_score:
        match.winner_team_id = match.home_team_id
        match.winner_team_name = match.home_team_name
    else:
        match.winner_team_id = match.away_team_id
        match.winner_team_name = match.away_team_name
    match.updated_at = datetime.now()
    db.commit()
    group_no = int(str(match.stage).split("_", 1)[1])
    score_label = "未赛" if home_score is None else f"{home_score}-{away_score}"
    write_to_log(
        "杯赛小组比分编辑",
        f"{CUP_DEFINITIONS[competition]['title']} {_group_name(group_no)} 组第 {((match.slot_no - 1) // 3) + 1} 轮：{match.home_team_name} {score_label} {match.away_team_name}",
        operator,
    )
    return {"success": True, "message": "小组赛比分已保存"}


def _visible_team(db: Session, team_id: int | None) -> Team | None:
    if team_id is None:
        return None
    team = get_team_by_id(db, team_id)
    if not team or team.level == VISIBLE_LEVEL:
        raise HTTPException(status_code=400, detail="请选择已有可见球队")
    return team


def _set_team(match: CupMatch, side: str, team: Team | None) -> None:
    setattr(match, f"{side}_team_id", team.id if team else None)
    setattr(match, f"{side}_team_name", team.name if team else None)


def _stage_index(competition: str, stage: str) -> int:
    stages = get_cup_stages(competition)
    for index, (key, _label, _count) in enumerate(stages):
        if key == stage:
            return index
    raise HTTPException(status_code=400, detail="杯赛阶段无效")


def _next_slot(match: CupMatch) -> tuple[str, int, str] | None:
    if match.competition == "wumingjian_cup" and match.stage == WUMINGJIAN_QUALIFYING_STAGE:
        return None
    stages = get_cup_stages(match.competition)
    index = _stage_index(match.competition, match.stage)
    if index >= len(stages) - 1:
        return None
    next_stage = stages[index + 1][0]
    next_slot_no = (match.slot_no + 1) // 2
    side = "home" if match.slot_no % 2 == 1 else "away"
    return next_stage, next_slot_no, side


def _team_advancement(match: CupMatch, side: str) -> str:
    team_id = getattr(match, f"{side}_team_id")
    if match.status != "played" or not team_id or not match.winner_team_id:
        return "pending"
    return "winner" if int(team_id) == int(match.winner_team_id) else "eliminated"


def _cup_match_response(match: CupMatch) -> CupMatchResponse:
    return CupMatchResponse(
        id=match.id,
        competition=match.competition,
        stage=match.stage,
        slot_no=match.slot_no,
        home_team_id=match.home_team_id,
        home_team_name=match.home_team_name,
        away_team_id=match.away_team_id,
        away_team_name=match.away_team_name,
        home_score=match.home_score,
        away_score=match.away_score,
        winner_team_id=match.winner_team_id,
        winner_team_name=match.winner_team_name,
        home_advancement=_team_advancement(match, "home"),
        away_advancement=_team_advancement(match, "away"),
        status=match.status,
        notes=match.notes,
        updated_at=match.updated_at,
    )


def _clear_winner(match: CupMatch) -> None:
    match.winner_team_id = None
    match.winner_team_name = None
    match.status = "scheduled"


def _set_match_winner(match: CupMatch, winner_team_id: int) -> None:
    if int(winner_team_id) == int(match.home_team_id):
        match.winner_team_id = match.home_team_id
        match.winner_team_name = match.home_team_name
        return
    if int(winner_team_id) == int(match.away_team_id):
        match.winner_team_id = match.away_team_id
        match.winner_team_name = match.away_team_name
        return
    raise HTTPException(status_code=400, detail="晋级球队必须是本场对阵双方之一")


def _clear_downstream(db: Session, competition: str, stage: str, slot_no: int, side: str | None = None) -> None:
    match = (
        db.query(CupMatch)
        .filter(CupMatch.competition == competition, CupMatch.stage == stage, CupMatch.slot_no == slot_no)
        .first()
    )
    if not match:
        return
    if side:
        _set_team(match, side, None)
    match.home_score = None
    match.away_score = None
    _clear_winner(match)
    match.updated_at = datetime.now()
    next_target = _next_slot(match)
    if next_target:
        _clear_downstream(db, competition, *next_target)


def _propagate_winner(db: Session, match: CupMatch) -> None:
    next_target = _next_slot(match)
    if not next_target:
        return
    next_stage, next_slot_no, side = next_target
    next_match = (
        db.query(CupMatch)
        .filter(CupMatch.competition == match.competition, CupMatch.stage == next_stage, CupMatch.slot_no == next_slot_no)
        .first()
    )
    if not next_match:
        return
    old_team_id = getattr(next_match, f"{side}_team_id")
    if old_team_id != match.winner_team_id:
        _clear_downstream(db, match.competition, next_stage, next_slot_no, side)
    team = _visible_team(db, match.winner_team_id) if match.winner_team_id else None
    _set_team(next_match, side, team)
    next_match.updated_at = datetime.now()


def initialize_cup_bracket(
    db: Session,
    admin: str | None,
    competition: str,
    write_to_log: LogWriter,
    *,
    reset: bool = False,
) -> dict[str, Any]:
    operator = require_admin(admin)
    competition = normalize_competition(competition)
    created = ensure_bracket(db, competition)
    title = CUP_DEFINITIONS[competition]["title"]
    if not reset:
        write_to_log("杯赛初始化", f"{title} 初始化，新增 {created} 个槽位", operator)
        message = f"{title} 淘汰赛已初始化" if created else f"{title} 淘汰赛已存在，无需重复初始化"
        return {"success": True, "message": message}

    knockout_stage_keys = [stage for stage, _label, _count in get_cup_stages(competition)]
    if competition == "wumingjian_cup":
        knockout_stage_keys.insert(0, WUMINGJIAN_QUALIFYING_STAGE)
    matches = (
        db.query(CupMatch)
        .filter(CupMatch.competition == competition, CupMatch.stage.in_(knockout_stage_keys))
        .all()
    )
    cleared = 0
    updated_at = datetime.now()
    for match in matches:
        if any(
            value is not None
            for value in (
                match.home_team_id,
                match.home_team_name,
                match.away_team_id,
                match.away_team_name,
                match.home_score,
                match.away_score,
                match.winner_team_id,
                match.winner_team_name,
                match.notes,
            )
        ) or match.status != "scheduled":
            cleared += 1
        match.home_team_id = None
        match.home_team_name = None
        match.away_team_id = None
        match.away_team_name = None
        match.home_score = None
        match.away_score = None
        match.winner_team_id = None
        match.winner_team_name = None
        match.status = "scheduled"
        match.notes = None
        match.updated_at = updated_at
    if competition == "wumingjian_cup":
        db.query(WumingjianQualificationTeam).delete(synchronize_session=False)
    db.commit()
    write_to_log(
        "杯赛初始化",
        f"{title} 重新初始化，重置 {len(matches)} 个槽位，清除 {cleared} 个已有对阵",
        operator,
    )
    return {
        "success": True,
        "message": f"{title} 已重新初始化，共重置 {len(matches)} 个对阵槽位",
    }


def update_cup_match_teams(
    db: Session,
    admin: str | None,
    match_id: int,
    request: CupMatchTeamsUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    match = db.query(CupMatch).filter(CupMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="杯赛对阵不存在")
    manually_editable_stage = match.stage == get_first_stage(match.competition) or (
        match.competition == "wumingjian_cup"
        and match.stage in {WUMINGJIAN_QUALIFYING_STAGE, "round_of_32"}
    )
    if not manually_editable_stage:
        raise HTTPException(status_code=400, detail="只能手动编辑杯赛首轮球队，后续轮次由晋级自动生成")
    home = _visible_team(db, request.home_team_id)
    away = _visible_team(db, request.away_team_id)
    if home and away and home.id == away.id:
        raise HTTPException(status_code=400, detail="同一场对阵不能选择相同球队")
    if match.competition == "wumingjian_cup":
        qualification_rows = _lock_wumingjian_qualification(db)
        if match.stage == WUMINGJIAN_QUALIFYING_STAGE:
            eligible_ids = {
                int(row["team_id"])
                for row in qualification_rows
                if row["qualification_type"] == "preliminary"
            }
            invalid_message = "预选赛只能选择未直通32强的44支球队"
        else:
            qualifying_matches = (
                db.query(CupMatch)
                .filter(
                    CupMatch.competition == "wumingjian_cup",
                    CupMatch.stage == WUMINGJIAN_QUALIFYING_STAGE,
                )
                .all()
            )
            winner_ids = {
                int(item.winner_team_id)
                for item in qualifying_matches
                if item.status == "played" and item.winner_team_id
            }
            if len(winner_ids) != WUMINGJIAN_QUALIFYING_MATCH_COUNT:
                raise HTTPException(status_code=400, detail="22场预选赛尚未全部决出胜者，暂不能编排32强对阵")
            eligible_ids = {
                int(row["team_id"])
                for row in qualification_rows
                if row["qualification_type"] == "direct"
            } | winner_ids
            invalid_message = "32强只能选择10支直通球队或22支预选赛胜者"
        for team in (home, away):
            if team and int(team.id) not in eligible_ids:
                raise HTTPException(status_code=400, detail=invalid_message)
        selected_ids = {int(team.id) for team in (home, away) if team}
        if selected_ids:
            duplicate = (
                db.query(CupMatch)
                .filter(
                    CupMatch.competition == "wumingjian_cup",
                    CupMatch.stage == match.stage,
                    CupMatch.id != match.id,
                    (
                        CupMatch.home_team_id.in_(selected_ids)
                        | CupMatch.away_team_id.in_(selected_ids)
                    ),
                )
                .first()
            )
            if duplicate:
                raise HTTPException(status_code=400, detail="同一支球队不能在本阶段重复参加对阵")
    _set_team(match, "home", home)
    _set_team(match, "away", away)
    match.home_score = None
    match.away_score = None
    match.notes = str(request.notes or "").strip() or None
    _clear_winner(match)
    match.updated_at = datetime.now()
    next_target = _next_slot(match)
    if next_target:
        _clear_downstream(db, match.competition, *next_target)
    db.commit()
    write_to_log("杯赛球队编辑", f"{CUP_DEFINITIONS[match.competition]['title']} {match.stage} #{match.slot_no}", operator)
    return {"success": True, "message": "杯赛对阵球队已保存"}


def update_cup_match_result(
    db: Session,
    admin: str | None,
    match_id: int,
    request: CupMatchResultUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    match = db.query(CupMatch).filter(CupMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="杯赛对阵不存在")
    if not match.home_team_id or not match.away_team_id:
        raise HTTPException(status_code=400, detail="请先选择双方球队")
    status = str(request.status or "").strip().lower() or "scheduled"
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="比赛状态仅支持 scheduled 或 played")
    home_score = request.home_score
    away_score = request.away_score
    if status == "played":
        if home_score is None or away_score is None:
            raise HTTPException(status_code=400, detail="已赛比赛必须填写比分")
        if home_score < 0 or away_score < 0:
            raise HTTPException(status_code=400, detail="比分不能为负数")
        if home_score == away_score:
            if not request.winner_team_id:
                raise HTTPException(status_code=400, detail="总比分相同，请按客场进球规则选择晋级球队")
            if request.advancement_reason not in {"away_goals", "extra_time", "penalties", "other"}:
                raise HTTPException(status_code=400, detail="总比分相同，请记录晋级原因")
            _set_match_winner(match, int(request.winner_team_id))
        else:
            _set_match_winner(match, match.home_team_id if home_score > away_score else match.away_team_id)
    else:
        next_target = _next_slot(match)
        if next_target:
            _clear_downstream(db, match.competition, *next_target)
        _clear_winner(match)
    match.home_score = home_score
    match.away_score = away_score
    match.status = status
    notes = str(request.notes or "").strip()
    if status == "played" and home_score == away_score and not notes:
        reason_labels = {
            "away_goals": "客场进球",
            "extra_time": "加时赛",
            "penalties": "点球大战",
            "other": "其他规则",
        }
        notes = f"总比分相同，按{reason_labels.get(request.advancement_reason, '人工确认')}晋级"
    match.notes = notes or None
    match.updated_at = datetime.now()
    if status == "played":
        _propagate_winner(db, match)
    db.commit()
    write_to_log("杯赛比分编辑", f"{CUP_DEFINITIONS[match.competition]['title']} {match.stage} #{match.slot_no}", operator)
    return {"success": True, "message": "杯赛比分已保存"}


def list_cup_team_options(db: Session) -> list[dict[str, Any]]:
    return [
        {"id": team.id, "name": team.name, "manager": team.manager, "level": team.level}
        for team in sorted(list_visible_teams(db, VISIBLE_LEVEL), key=lambda item: (item.level, item.name))
    ]
