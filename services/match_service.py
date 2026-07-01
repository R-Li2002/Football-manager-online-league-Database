from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Any

from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from models import Match
from repositories.match_repository import (
    delete_matches_not_in_keys,
    find_match_by_fixture,
    get_match_by_id,
    list_matches,
    list_played_matches,
)
from repositories.team_repository import get_team_by_name, list_visible_teams
from schemas_read import MatchResponse, ScheduleResponse, StandingRowResponse, StandingsResponse
from schemas_write import MatchBatchUpdateRequest, MatchUpdateRequest, ScheduleImportResponse
from services.admin_common import LogWriter, require_admin

LEVEL_ORDER = {"超级": 1, "甲级": 2, "乙级": 3}
VISIBLE_LEVEL = "隐藏"
MATCH_STATUSES = {"scheduled", "played", "postponed", "cancelled"}
SCHEDULE_ROOT = Path("imports") / "schedules"


@dataclass(frozen=True)
class ParsedFixture:
    level: str
    round_no: int
    home_team_name: str
    away_team_name: str


def _normalize_cell(value: Any) -> str:
    return str(value or "").strip()


def _normalize_level(sheet_title: str) -> str:
    title = sheet_title.strip()
    for level in LEVEL_ORDER:
        if level in title:
            return level
    return title.replace("赛程", "").strip() or title


def _parse_round_no(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and int(value) == value:
        return int(value)
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def _parse_fixture_sheet(ws, level: str) -> list[ParsedFixture]:
    fixtures: list[ParsedFixture] = []
    active_rounds: dict[int, int] = {}

    for row in ws.iter_rows(values_only=True):
        cells = list(row)
        round_positions = {
            index: round_no
            for index, value in enumerate(cells)
            if (round_no := _parse_round_no(value)) is not None
            and _normalize_cell(cells[index - 1] if index > 0 else "") == ""
        }
        if round_positions:
            active_rounds.update(round_positions)
            continue

        for round_col, round_no in active_rounds.items():
            home = _normalize_cell(cells[round_col - 1] if round_col - 1 >= 0 and round_col - 1 < len(cells) else "")
            marker = _normalize_cell(cells[round_col] if round_col < len(cells) else "").lower()
            away = _normalize_cell(cells[round_col + 1] if round_col + 1 < len(cells) else "")
            if home and away and marker == "vs":
                fixtures.append(
                    ParsedFixture(
                        level=level,
                        round_no=round_no,
                        home_team_name=home,
                        away_team_name=away,
                    )
                )
    return fixtures


def find_latest_schedule_file(root: Path = SCHEDULE_ROOT) -> Path:
    candidates = [
        path
        for pattern in ("*.xlsx", "*.xlsm")
        for path in root.glob(pattern)
        if path.is_file() and not path.name.startswith("~$")
    ]
    if not candidates:
        raise HTTPException(status_code=404, detail=f"未在 {root} 找到赛程 Excel 文件")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def parse_schedule_workbook(path: Path) -> list[ParsedFixture]:
    workbook = load_workbook(path, data_only=True)
    fixtures: list[ParsedFixture] = []
    for ws in workbook.worksheets:
        level = _normalize_level(ws.title)
        fixtures.extend(_parse_fixture_sheet(ws, level))
    if not fixtures:
        raise HTTPException(status_code=400, detail="赛程文件中没有识别到任何 主队 vs 客队 对阵")
    return fixtures


def import_latest_schedule(db: Session, admin: str | None, write_to_log: LogWriter) -> ScheduleImportResponse:
    operator = require_admin(admin)
    path = find_latest_schedule_file()
    fixtures = parse_schedule_workbook(path)
    team_by_name = {team.name: team for team in list_visible_teams(db, VISIBLE_LEVEL)}
    fixture_keys = {(item.level, item.round_no, item.home_team_name, item.away_team_name) for item in fixtures}
    warnings: list[str] = []
    created = updated = unchanged = 0

    for item in fixtures:
        home_team = team_by_name.get(item.home_team_name)
        away_team = team_by_name.get(item.away_team_name)
        if not home_team:
            warnings.append(f"未匹配主队：{item.home_team_name}")
        if not away_team:
            warnings.append(f"未匹配客队：{item.away_team_name}")

        match = find_match_by_fixture(
            db,
            level=item.level,
            round_no=item.round_no,
            home_team_name=item.home_team_name,
            away_team_name=item.away_team_name,
        )
        if not match:
            db.add(
                Match(
                    season_label=path.stem,
                    level=item.level,
                    round_no=item.round_no,
                    home_team_id=home_team.id if home_team else None,
                    home_team_name=item.home_team_name,
                    away_team_id=away_team.id if away_team else None,
                    away_team_name=item.away_team_name,
                    status="scheduled",
                    source_file=str(path),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
            created += 1
            continue

        changed = False
        for field_name, value in (
            ("season_label", path.stem),
            ("home_team_id", home_team.id if home_team else None),
            ("away_team_id", away_team.id if away_team else None),
            ("source_file", str(path)),
        ):
            if getattr(match, field_name) != value:
                setattr(match, field_name, value)
                changed = True
        if changed:
            match.updated_at = datetime.now()
            updated += 1
        else:
            unchanged += 1

    removed = delete_matches_not_in_keys(db, fixture_keys)
    db.commit()
    message = f"赛程导入完成：新增 {created}，更新 {updated}，未变 {unchanged}，移除 {removed}"
    write_to_log("赛程导入", f"{message}; source={path}", operator)
    return ScheduleImportResponse(
        success=True,
        message=message,
        source_file=str(path),
        created=created,
        updated=updated,
        unchanged=unchanged,
        removed=removed,
        warnings=sorted(set(warnings)),
    )


def get_schedule(db: Session, *, level: str | None = None, round_no: int | None = None) -> ScheduleResponse:
    matches = list_matches(db, level=level, round_no=round_no)
    return ScheduleResponse(
        levels=sorted({match.level for match in matches}, key=lambda item: (LEVEL_ORDER.get(item, 99), item)),
        rounds=sorted({match.round_no for match in matches}),
        matches=[MatchResponse.model_validate(match) for match in matches],
    )


def get_standings(db: Session) -> StandingsResponse:
    teams = sorted(list_visible_teams(db, VISIBLE_LEVEL), key=lambda team: (LEVEL_ORDER.get(team.level, 99), team.name))
    rows_by_team = {
        team.name: {
            "level": team.level,
            "team_id": team.id,
            "team_name": team.name,
            "manager": team.manager,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
            "goal_rate": 0.0,
            "win_rate": 0.0,
            "home_played": 0,
            "home_wins": 0,
            "home_draws": 0,
            "home_losses": 0,
            "home_goals_for": 0,
            "home_goals_against": 0,
            "home_goal_difference": 0,
            "home_points": 0,
            "home_win_rate": 0.0,
            "away_played": 0,
            "away_wins": 0,
            "away_draws": 0,
            "away_losses": 0,
            "away_goals_for": 0,
            "away_goals_against": 0,
            "away_goal_difference": 0,
            "away_points": 0,
            "away_win_rate": 0.0,
        }
        for team in teams
    }
    rows_by_team_id = {row["team_id"]: row for row in rows_by_team.values() if row["team_id"] is not None}

    for match in list_played_matches(db):
        home = rows_by_team_id.get(match.home_team_id) if match.home_team_id is not None else None
        away = rows_by_team_id.get(match.away_team_id) if match.away_team_id is not None else None
        home = home or rows_by_team.get(match.home_team_name)
        away = away or rows_by_team.get(match.away_team_name)
        if not home or not away:
            continue
        home_score = int(match.home_score or 0)
        away_score = int(match.away_score or 0)

        home["played"] += 1
        away["played"] += 1
        home["home_played"] += 1
        away["away_played"] += 1
        home["goals_for"] += home_score
        home["goals_against"] += away_score
        away["goals_for"] += away_score
        away["goals_against"] += home_score
        home["home_goals_for"] += home_score
        home["home_goals_against"] += away_score
        away["away_goals_for"] += away_score
        away["away_goals_against"] += home_score

        if home_score > away_score:
            home["wins"] += 1
            home["home_wins"] += 1
            home["points"] += 3
            home["home_points"] += 3
            away["losses"] += 1
            away["away_losses"] += 1
        elif home_score < away_score:
            away["wins"] += 1
            away["away_wins"] += 1
            away["points"] += 3
            away["away_points"] += 3
            home["losses"] += 1
            home["home_losses"] += 1
        else:
            home["draws"] += 1
            home["home_draws"] += 1
            away["draws"] += 1
            away["away_draws"] += 1
            home["points"] += 1
            away["points"] += 1
            home["home_points"] += 1
            away["away_points"] += 1

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows_by_team.values():
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        row["home_goal_difference"] = row["home_goals_for"] - row["home_goals_against"]
        row["away_goal_difference"] = row["away_goals_for"] - row["away_goals_against"]
        row["goal_rate"] = round((row["goals_for"] / row["played"]), 2) if row["played"] else 0.0
        row["win_rate"] = round((row["wins"] / row["played"] * 100), 1) if row["played"] else 0.0
        row["home_win_rate"] = round((row["home_wins"] / row["home_played"] * 100), 1) if row["home_played"] else 0.0
        row["away_win_rate"] = round((row["away_wins"] / row["away_played"] * 100), 1) if row["away_played"] else 0.0
        grouped.setdefault(row["level"], []).append(row)

    response_rows: list[StandingRowResponse] = []
    for level in sorted(grouped, key=lambda item: (LEVEL_ORDER.get(item, 99), item)):
        ranked_rows = sorted(
            grouped[level],
            key=lambda row: (
                -row["points"],
                -row["goal_difference"],
                -row["goals_for"],
                -row["wins"],
                row["team_name"],
            ),
        )
        for index, row in enumerate(ranked_rows, start=1):
            response_rows.append(StandingRowResponse(rank=index, **row))

    return StandingsResponse(
        levels=sorted(grouped, key=lambda item: (LEVEL_ORDER.get(item, 99), item)),
        rows=response_rows,
    )


def _parse_match_date(value: str | None):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail="比赛日期格式应为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM")


def _normalize_status(request: MatchUpdateRequest) -> str:
    status = str(request.status or "").strip().lower()
    has_score = request.home_score is not None and request.away_score is not None
    if not status:
        return "played" if has_score else "scheduled"
    if status not in MATCH_STATUSES:
        raise HTTPException(status_code=400, detail="比赛状态仅支持 scheduled、played、postponed、cancelled")
    return status


def _apply_match_result_update(match: Match, request: MatchUpdateRequest) -> None:
    status = _normalize_status(request)
    if status == "played":
        if request.home_score is None or request.away_score is None:
            raise HTTPException(status_code=400, detail="已赛比赛必须填写双方比分")
        if request.home_score < 0 or request.away_score < 0:
            raise HTTPException(status_code=400, detail="比分不能为负数")

    match.home_score = request.home_score if request.home_score is not None else None
    match.away_score = request.away_score if request.away_score is not None else None
    match.status = status
    if hasattr(request, "match_date"):
        match.match_date = _parse_match_date(request.match_date)
    match.notes = str(request.notes or "").strip() or None
    match.updated_at = datetime.now()


def update_match_result(
    db: Session,
    admin: str | None,
    match_id: int,
    request: MatchUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    match = get_match_by_id(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="比赛不存在")

    _apply_match_result_update(match, request)
    db.commit()

    score_text = "-" if match.home_score is None or match.away_score is None else f"{match.home_score}-{match.away_score}"
    message = f"已更新第 {match.round_no} 轮 {match.home_team_name} vs {match.away_team_name}：{score_text}"
    write_to_log("赛程比分编辑", message, operator)
    return {"success": True, "message": message}


def batch_update_match_results(
    db: Session,
    admin: str | None,
    request: MatchBatchUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    if not request.matches:
        raise HTTPException(status_code=400, detail="没有需要保存的比赛")

    seen_ids: set[int] = set()
    updated = 0
    for item in request.matches:
        if item.match_id in seen_ids:
            continue
        seen_ids.add(item.match_id)
        match = get_match_by_id(db, item.match_id)
        if not match:
            raise HTTPException(status_code=404, detail=f"比赛不存在：{item.match_id}")
        _apply_match_result_update(
            match,
            MatchUpdateRequest(
                home_score=item.home_score,
                away_score=item.away_score,
                status=item.status,
                notes=item.notes,
            ),
        )
        updated += 1

    db.commit()
    message = f"已保存 {updated} 场比赛进展"
    write_to_log("赛程比分批量编辑", message, operator)
    return {"success": True, "message": message}
