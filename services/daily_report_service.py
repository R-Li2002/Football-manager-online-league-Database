from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256
import json
from string import Formatter
import time as monotonic_time
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import (
    CupMatch,
    DailyReport,
    DailyReportNarrativeTemplate,
    Match,
    MatchPlayerEvent,
    OperationAudit,
    PlayerSuspensionRecord,
)
from schemas_read import DailyReportNarrativeTemplateResponse, DailyReportResponse, WorkspaceIdentityResponse
from schemas_write import DailyReportNarrativeTemplateUpsertRequest, DailyReportUpdateRequest
from services import cup_service, match_service, player_power_ranking_service, team_name_service


BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
LEAGUE_LEVELS = ("超级", "甲级", "乙级")
PLAYED_MATCH_STATUSES = {"played", "home_forfeit", "away_forfeit", "double_forfeit"}
FORFEIT_MATCH_STATUSES = {"home_forfeit", "away_forfeit", "double_forfeit"}
REPORT_STATUSES = {"draft", "published"}
ALLOWED_TEMPLATE_FIELDS = {
    "winner", "loser", "home_team", "away_team", "home_score", "away_score", "score",
    "total_goals", "margin", "competition", "stage", "player", "team", "goals", "assists",
    "winner_power", "loser_power", "power_gap",
    "team_a", "team_b", "aggregate_score", "series_goals", "first_leg", "second_leg",
}
CATEGORY_LABELS = {
    "narrow_win": "一球小胜",
    "regular_win": "普通胜利",
    "big_win": "大比分胜利",
    "clean_sheet_rout": "零封大胜",
    "high_scoring_win": "高比分胜利",
    "goalless_draw": "0:0 闷平",
    "draw": "普通平局",
    "high_scoring_draw": "高比分平局",
    "forfeit": "判负结果",
    "double_forfeit": "双方判负",
    "winning_hattrick": "胜方帽子戏法",
    "losing_hattrick": "败方帽子戏法",
    "hattrick": "平局帽子戏法",
    "brace": "梅开二度",
    "playmaker": "多次助攻",
    "goal_and_assist": "传射建功",
    "mvp": "本场最佳",
    "power_upset": "战力下风取胜",
    "power_close": "战力接近",
    "series_sweep": "两回合双杀",
    "series_split": "两回合各胜一场",
    "series_unbeaten": "两回合一胜一平",
    "series_draws": "两回合均战平",
}
AUTO_REPORT_CACHE_TTL_SECONDS = 180
MAX_FOCUS_STORIES = 6
_AUTO_REPORT_CACHE: dict[str, tuple[float, DailyReportResponse]] = {}


@dataclass(frozen=True)
class _FallbackTemplate:
    id: int
    category: str
    template_text: str
    sort_order: int = 100


FALLBACK_TEMPLATES = (
    _FallbackTemplate(1, "narrow_win", "{winner} {score} 险胜 {loser}，一球之差拿下关键胜利。"),
    _FallbackTemplate(2, "regular_win", "{winner} {score} 击败 {loser}，进攻效率更胜一筹。"),
    _FallbackTemplate(3, "big_win", "{winner} {score} 大胜 {loser}，进攻火力全面释放。"),
    _FallbackTemplate(4, "clean_sheet_rout", "{winner} {score} 完胜 {loser}，以一场强势零封收下胜利。"),
    _FallbackTemplate(5, "high_scoring_win", "{winner} {score} 力克 {loser}，双方联手轰入 {total_goals} 球，上演疯狂对攻。"),
    _FallbackTemplate(6, "goalless_draw", "{home_team} 与 {away_team} 互交白卷，双方在谨慎拉扯中各取一分。"),
    _FallbackTemplate(7, "draw", "{home_team} {score} 战平 {away_team}，鏖战过后握手言和。"),
    _FallbackTemplate(8, "high_scoring_draw", "{home_team} 与 {away_team} 大打对攻，最终 {score} 难分高下。"),
    _FallbackTemplate(9, "forfeit", "{winner} 因比赛判定取得本场结果，最终比分为 {score}。"),
    _FallbackTemplate(19, "double_forfeit", "{home_team} 与 {away_team} 本场均被判负，比赛按 {score} 记录。"),
    _FallbackTemplate(10, "winning_hattrick", "{player} 独中三元，成为 {team} 取胜的头号功臣。"),
    _FallbackTemplate(11, "losing_hattrick", "{player} 帽子戏法仍难救主，个人高光未能为 {team} 换来胜利。"),
    _FallbackTemplate(12, "hattrick", "{player} 上演帽子戏法，成为这场对攻战最耀眼的球员。"),
    _FallbackTemplate(13, "brace", "{player} 梅开二度，成为 {team} 进攻端最醒目的名字。"),
    _FallbackTemplate(14, "playmaker", "{player} 送出 {assists} 次助攻，成为 {team} 的进攻枢纽。"),
    _FallbackTemplate(15, "goal_and_assist", "{player} 贡献 {goals} 球 {assists} 助攻，在攻门与串联两端都有亮眼表现。"),
    _FallbackTemplate(16, "mvp", "{player} 当选本场最佳，成为这场比赛最受认可的球员。"),
    _FallbackTemplate(17, "power_upset", "赛前阵容战力处于下风的 {winner} 打出更高效率，击败了 {loser}。"),
    _FallbackTemplate(18, "power_close", "两队阵容战力十分接近，这场比赛也呈现出势均力敌的走势。"),
    _FallbackTemplate(20, "narrow_win", "{winner}以 {score} 擦过胜负线，{loser}距离改写结局只差一球。", 30),
    _FallbackTemplate(21, "regular_win", "{winner} {score} 击退 {loser}，用更直接的终结把差距写上比分牌。", 30),
    _FallbackTemplate(22, "big_win", "{winner} {score} 重创 {loser}，三球以上的优势彻底撕开了双方差距。", 30),
    _FallbackTemplate(23, "clean_sheet_rout", "{winner} {score} 零封横扫 {loser}，自己火力全开，也让对手的进球栏始终归零。", 30),
    _FallbackTemplate(24, "high_scoring_win", "{winner}在 {total_goals} 球对轰中以 {score} 笑到最后，进攻回击压过了防线失守。", 30),
    _FallbackTemplate(25, "goalless_draw", "{home_team}与{away_team}把进球栏锁成 0:0，整场拉扯最终只留下两张白卷。", 30),
    _FallbackTemplate(26, "draw", "{home_team}与{away_team}战成 {score}，谁也没能把有限优势真正写成胜果。", 30),
    _FallbackTemplate(27, "high_scoring_draw", "{home_team}与{away_team}轰出 {score}，合计 {total_goals} 球仍分不出赢家。", 30),
    _FallbackTemplate(28, "winning_hattrick", "{player} 一人轰入三球，几乎以个人名义接管了 {team} 的进攻头条。", 30),
    _FallbackTemplate(29, "losing_hattrick", "{player} 独中三元却只能目送 {team} 落败，最耀眼的个人演出撞上了最残酷的团队结果。", 30),
    _FallbackTemplate(30, "brace", "{player} 梅开二度，两次破门把名字牢牢钉在 {team} 本场的进攻主线上。", 30),
    _FallbackTemplate(31, "playmaker", "{player}送出 {assists} 次助攻，用传球连续撕开对手防线。", 30),
    _FallbackTemplate(32, "goal_and_assist", "{player} 交出 {goals} 球 {assists} 助攻，一人包办得分与输送两条火线。", 30),
    _FallbackTemplate(33, "mvp", "{player} 当选本场最佳，用全场最醒目的表现压过了其他竞争者。", 30),
    _FallbackTemplate(34, "power_upset", "纸面战力落后的 {winner} 掀翻 {loser}，用结果把 {power_gap} 点差距变成了赛前数字。", 30),
    _FallbackTemplate(35, "series_sweep", "{winner}两战通吃，以两回合总比分 {aggregate_score} 完成双杀。{first_leg}；{second_leg}，把胜果与气势一并收入囊中。", 10),
    _FallbackTemplate(36, "series_sweep", "{winner}包办两回合胜利，累计以 {aggregate_score} 压过 {loser}。{first_leg}；{second_leg}，主客场都没给对手留下胜果。", 20),
    _FallbackTemplate(37, "series_split", "{team_a}与{team_b}各赢一场，两回合针锋相对。{first_leg}；{second_leg}，胜负各自带走，悬念谁也没能独占。", 10),
    _FallbackTemplate(38, "series_split", "两回合演成一场隔空对攻：{first_leg}；{second_leg}。{team_a}与{team_b}各守一胜，谁也没能彻底压住对方。", 20),
    _FallbackTemplate(39, "series_unbeaten", "{winner}一胜一平保持不败，两回合总比分 {aggregate_score} 占据上风。{first_leg}；{second_leg}，没有让 {loser} 拿走完整胜果。", 10),
    _FallbackTemplate(40, "series_unbeaten", "{winner}用一胜一平接管两回合叙事：{first_leg}；{second_leg}。不败背后，是总比分 {aggregate_score} 的稳定压制。", 20),
    _FallbackTemplate(41, "series_draws", "两回合都没有赢家，{team_a}与{team_b}合计打入 {series_goals} 球。{first_leg}；{second_leg}，两次交锋都停在平局线上。", 10),
    _FallbackTemplate(42, "series_draws", "{team_a}与{team_b}连续两场互不相让：{first_leg}；{second_leg}。总计 {series_goals} 粒进球，仍没人带走胜利。", 20),
)


def _business_today() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()


def _parse_report_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if not raw:
        return _business_today()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日报日期必须使用 YYYY-MM-DD 格式") from exc


def _date_bounds(report_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(report_date, time.min)
    return start, start + timedelta(days=1)


def _require_daily_report_manager(identity: WorkspaceIdentityResponse) -> str:
    if not identity or (not identity.is_full_admin and "daily_reports.write" not in identity.capabilities):
        raise HTTPException(status_code=403, detail="当前账号没有日报维护权限")
    if identity.source == "coach_account":
        return identity.principal_id
    return identity.username or identity.display_name or identity.principal_id


def _audit(db: Session, operator: str, action: str, summary: str, details: dict[str, Any] | None = None) -> None:
    db.add(OperationAudit(
        category="content",
        action=action,
        status="success",
        source="admin_ui",
        operator=operator,
        summary=summary,
        details_json=json.dumps(details or {}, ensure_ascii=False),
        created_at=datetime.now(),
    ))


def _template_response(row: DailyReportNarrativeTemplate) -> DailyReportNarrativeTemplateResponse:
    return DailyReportNarrativeTemplateResponse(
        id=int(row.id),
        category=str(row.category),
        category_label=CATEGORY_LABELS.get(str(row.category), str(row.category)),
        name=str(row.name),
        template_text=str(row.template_text),
        is_active=bool(row.is_active),
        sort_order=int(row.sort_order or 100),
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validate_template_request(request: DailyReportNarrativeTemplateUpsertRequest) -> dict[str, Any]:
    category = str(request.category or "").strip()
    name = str(request.name or "").strip()
    template_text = str(request.template_text or "").strip()
    if category not in CATEGORY_LABELS:
        raise HTTPException(status_code=400, detail="未知的话术类别")
    if not name:
        raise HTTPException(status_code=400, detail="请填写话术名称")
    if not template_text:
        raise HTTPException(status_code=400, detail="请填写话术正文")
    if len(name) > 60 or len(template_text) > 320:
        raise HTTPException(status_code=400, detail="话术名称或正文过长")
    try:
        fields = {field_name for _, field_name, _, _ in Formatter().parse(template_text) if field_name}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="话术中的花括号格式不正确") from exc
    unsupported = sorted(fields - ALLOWED_TEMPLATE_FIELDS)
    if unsupported:
        raise HTTPException(status_code=400, detail=f"不支持的占位符：{', '.join(unsupported)}")
    return {
        "category": category,
        "name": name,
        "template_text": template_text,
        "is_active": 1 if request.is_active else 0,
        "sort_order": max(0, min(9999, int(request.sort_order or 100))),
    }


def list_templates(db: Session, identity: WorkspaceIdentityResponse) -> list[DailyReportNarrativeTemplateResponse]:
    _require_daily_report_manager(identity)
    rows = db.query(DailyReportNarrativeTemplate).order_by(
        DailyReportNarrativeTemplate.category,
        DailyReportNarrativeTemplate.sort_order,
        DailyReportNarrativeTemplate.id,
    ).all()
    return [_template_response(row) for row in rows]


def create_template(
    db: Session,
    identity: WorkspaceIdentityResponse,
    request: DailyReportNarrativeTemplateUpsertRequest,
) -> DailyReportNarrativeTemplateResponse:
    operator = _require_daily_report_manager(identity)
    now = datetime.now()
    row = DailyReportNarrativeTemplate(**_validate_template_request(request), created_by=operator, updated_by=operator, created_at=now, updated_at=now)
    db.add(row)
    db.flush()
    _audit(db, operator, "create_daily_report_template", f"新增日报话术：{row.name}", {"template_id": row.id, "category": row.category})
    db.commit()
    db.refresh(row)
    _AUTO_REPORT_CACHE.clear()
    return _template_response(row)


def update_template(
    db: Session,
    identity: WorkspaceIdentityResponse,
    template_id: int,
    request: DailyReportNarrativeTemplateUpsertRequest,
) -> DailyReportNarrativeTemplateResponse:
    operator = _require_daily_report_manager(identity)
    row = db.query(DailyReportNarrativeTemplate).filter(DailyReportNarrativeTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="日报话术不存在")
    for key, value in _validate_template_request(request).items():
        setattr(row, key, value)
    row.updated_by = operator
    row.updated_at = datetime.now()
    _audit(db, operator, "update_daily_report_template", f"更新日报话术：{row.name}", {"template_id": row.id, "category": row.category})
    db.commit()
    db.refresh(row)
    _AUTO_REPORT_CACHE.clear()
    return _template_response(row)


def delete_template(db: Session, identity: WorkspaceIdentityResponse, template_id: int) -> dict[str, str | bool]:
    operator = _require_daily_report_manager(identity)
    row = db.query(DailyReportNarrativeTemplate).filter(DailyReportNarrativeTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="日报话术不存在")
    name = row.name
    db.delete(row)
    _audit(db, operator, "delete_daily_report_template", f"删除日报话术：{name}", {"template_id": template_id})
    db.commit()
    _AUTO_REPORT_CACHE.clear()
    return {"success": True, "message": "日报话术已删除"}


def _template_pool(db: Session) -> dict[str, list[Any]]:
    all_rows = db.query(DailyReportNarrativeTemplate).order_by(
        DailyReportNarrativeTemplate.category,
        DailyReportNarrativeTemplate.sort_order,
        DailyReportNarrativeTemplate.id,
    ).all()
    source = [row for row in all_rows if bool(row.is_active)] if all_rows else FALLBACK_TEMPLATES
    pool: dict[str, list[Any]] = defaultdict(list)
    for row in source:
        pool[str(row.category)].append(row)
    return pool


def _render_template(pool: dict[str, list[Any]], category: str, context: dict[str, Any], seed: str) -> str:
    rows = pool.get(category) or []
    if not rows:
        return ""
    digest = int(sha256(f"{seed}:{category}".encode("utf-8")).hexdigest()[:12], 16)
    row = rows[digest % len(rows)]
    values = defaultdict(str, {key: str(value) for key, value in context.items()})
    try:
        return str(row.template_text).format_map(values).strip()
    except (KeyError, ValueError):
        return ""


def _match_category(match: Match | CupMatch) -> str:
    home = int(match.home_score or 0)
    away = int(match.away_score or 0)
    total = home + away
    if str(match.status) == "double_forfeit":
        return "double_forfeit"
    if str(match.status) in FORFEIT_MATCH_STATUSES:
        return "forfeit"
    if home == away:
        if total == 0:
            return "goalless_draw"
        return "high_scoring_draw" if total >= 6 else "draw"
    margin = abs(home - away)
    losing_score = min(home, away)
    if total >= 7 and losing_score >= 2:
        return "high_scoring_win"
    if losing_score == 0 and margin >= 4:
        return "clean_sheet_rout"
    if margin >= 3:
        return "big_win"
    if margin == 1:
        return "narrow_win"
    return "regular_win"


def _match_context(match: Match | CupMatch, competition: str, stage: str) -> dict[str, Any]:
    home_score = int(match.home_score or 0)
    away_score = int(match.away_score or 0)
    is_draw = home_score == away_score
    home_wins = home_score > away_score
    winner = match.home_team_name if home_wins else match.away_team_name
    loser = match.away_team_name if home_wins else match.home_team_name
    score = f"{home_score}:{away_score}" if is_draw or home_wins else f"{away_score}:{home_score}"
    if is_draw:
        winner = ""
        loser = ""
    return {
        "winner": winner or "比赛胜方",
        "loser": loser or "比赛负方",
        "home_team": match.home_team_name or "主队",
        "away_team": match.away_team_name or "客队",
        "home_score": home_score,
        "away_score": away_score,
        "score": score,
        "total_goals": home_score + away_score,
        "margin": abs(home_score - away_score),
        "competition": competition,
        "stage": stage,
    }


def _event_stats(events: list[MatchPlayerEvent]) -> list[dict[str, Any]]:
    by_player: dict[tuple[str, int, str], dict[str, Any]] = {}
    for event in events:
        if event.event_type == "own_goal":
            continue
        key = (str(event.team_name or ""), int(event.player_uid or 0), str(event.player_name or ""))
        row = by_player.setdefault(key, {
            "team": str(event.team_name or ""),
            "player": str(event.player_name or ""),
            "goals": 0,
            "assists": 0,
            "mvp": False,
        })
        quantity = max(0, int(event.quantity or 0))
        if event.event_type == "goal":
            row["goals"] += quantity
        elif event.event_type == "assist":
            row["assists"] += quantity
        elif event.event_type == "mvp":
            row["mvp"] = True
    return list(by_player.values())


def _player_highlight(
    pool: dict[str, list[Any]],
    stats: list[dict[str, Any]],
    context: dict[str, Any],
    seed: str,
) -> tuple[str, str]:
    if not stats:
        return "", ""
    winner = str(context.get("winner") or "")
    loser = str(context.get("loser") or "")
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for row in stats:
        team = str(row["team"])
        goals = int(row["goals"])
        assists = int(row["assists"])
        if goals >= 3 and loser and team == loser:
            candidates.append((100 + goals, "losing_hattrick", row))
        elif goals >= 3 and winner and team == winner:
            candidates.append((95 + goals, "winning_hattrick", row))
        elif goals >= 3:
            candidates.append((92 + goals, "hattrick", row))
        elif goals > 0 and assists > 0:
            candidates.append((80 + goals + assists, "goal_and_assist", row))
        elif goals >= 2:
            candidates.append((70 + goals, "brace", row))
        elif assists >= 2:
            candidates.append((60 + assists, "playmaker", row))
        elif row["mvp"]:
            candidates.append((50, "mvp", row))
    if not candidates:
        return "", ""
    _priority, category, selected = sorted(candidates, key=lambda item: (-item[0], item[2]["player"]))[0]
    return _render_template(pool, category, selected, seed), str(selected.get("player") or "")


def _player_phrase(
    pool: dict[str, list[Any]],
    stats: list[dict[str, Any]],
    context: dict[str, Any],
    seed: str,
) -> str:
    return _player_highlight(pool, stats, context, seed)[0]


def _power_values(db: Session) -> dict[str, float]:
    try:
        response = player_power_ranking_service.get_team_power_summaries(db)
    except Exception:
        return {}
    values: dict[str, float] = {}
    for item in response.items:
        value = item.lineup_average if item.lineup_average is not None else item.roster_average
        if value is not None:
            values[str(item.team_name)] = float(value)
    return values


def _power_phrase(
    pool: dict[str, list[Any]],
    context: dict[str, Any],
    power_values: dict[str, float],
    seed: str,
) -> str:
    winner = str(context.get("winner") or "")
    loser = str(context.get("loser") or "")
    home = str(context.get("home_team") or "")
    away = str(context.get("away_team") or "")
    if winner and loser and winner in power_values and loser in power_values:
        winner_power = power_values[winner]
        loser_power = power_values[loser]
        if loser_power - winner_power >= 2.5:
            power_context = {
                **context,
                "winner_power": f"{winner_power:.1f}",
                "loser_power": f"{loser_power:.1f}",
                "power_gap": f"{loser_power - winner_power:.1f}",
            }
            return _render_template(pool, "power_upset", power_context, seed)
    if home in power_values and away in power_values and abs(power_values[home] - power_values[away]) <= 0.75:
        return _render_template(pool, "power_close", context, seed)
    return ""


def _cup_stage_label(match: CupMatch) -> str:
    stage = str(match.stage or "")
    if stage.startswith("group_"):
        try:
            group_no = int(stage.split("_", 1)[1])
            round_no = (int(match.slot_no or 1) - 1) // 3 + 1
            return f"{chr(64 + group_no)}组第{round_no}轮"
        except (TypeError, ValueError):
            return "小组赛"
    for stage_key, label, _count in cup_service.get_cup_stages(str(match.competition)):
        if stage_key == stage:
            return label.replace("（上方主场）", "").replace("（下方主场）", "")
    return stage or "杯赛"


def _suspension_label(row: PlayerSuspensionRecord) -> str:
    parts: list[str] = []
    if bool(row.yellow_card_suspended):
        parts.append("3黄停赛")
    if int(row.yellow_cards or 0) > 0:
        parts.append(f"额外{int(row.yellow_cards)}黄")
    if bool(row.red_card_suspended):
        parts.append("红牌停赛")
    if bool(row.red_injury_suspended):
        parts.append("红伤停赛")
    if bool(row.yellow_card_suspended) or bool(row.red_card_suspended) or bool(row.red_injury_suspended):
        parts.append(f"停赛{max(1, int(row.suspension_matches or 1))}场")
    if row.notes:
        parts.append(str(row.notes).strip())
    return "、".join(parts) or "状态已更新"


def _upcoming_power_lines(db: Session, power_values: dict[str, float]) -> list[str]:
    lines: list[str] = []
    for level in LEAGUE_LEVELS:
        matches = db.query(Match).filter(
            Match.level == level,
            Match.status.in_(("scheduled", "postponed")),
            Match.home_score.is_(None),
            Match.away_score.is_(None),
        ).order_by(Match.round_no, Match.id).all()
        if not matches:
            continue
        next_round = min(int(match.round_no or 0) for match in matches)
        candidates = [match for match in matches if int(match.round_no or 0) == next_round]
        powered = [match for match in candidates if match.home_team_name in power_values and match.away_team_name in power_values]
        if not powered:
            continue
        match = min(powered, key=lambda item: abs(power_values[item.home_team_name] - power_values[item.away_team_name]))
        home_power = power_values[match.home_team_name]
        away_power = power_values[match.away_team_name]
        gap = abs(home_power - away_power)
        tone = "实力十分接近" if gap <= 0.75 else "存在一定战力差" if gap < 2.5 else "战力差距较为明显"
        lines.append(f"{level}第{next_round}轮｜{match.home_team_name} vs {match.away_team_name}：{home_power:.1f} 对 {away_power:.1f}，{tone}。")
    return lines


def _fingerprint(report_date: date, title: str, content: str) -> str:
    return sha256(f"{report_date.isoformat()}\n{title}\n{content}".encode("utf-8")).hexdigest()


def _report_image_url(report_date: str, fingerprint: str) -> str:
    return f"/api/daily-report/image?report_date={report_date}&fingerprint={fingerprint[:16]}"


def _focus_teams(db: Session) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    try:
        standings = match_service.get_standings(db)
    except Exception:
        return result
    for level in standings.levels:
        rows = [row for row in standings.rows if row.level == level]
        summary = next((item for item in standings.prediction_summaries if item.level == level), None)

        def normalized_set(items) -> set[str]:
            return {match_service._normalize_team_lookup_name(row.team_name) for row in items}

        title_candidates = sorted(rows, key=lambda row: (-float(row.title_race_probability), row.predicted_rank, row.rank))
        title_candidates = [row for row in title_candidates if float(row.title_race_probability) >= 0.12][:5] or rows[:2]
        promotion_candidates = sorted(rows, key=lambda row: (-float(row.promotion_probability), row.predicted_rank, row.rank))
        promotion_candidates = [row for row in promotion_candidates if float(row.promotion_probability) >= 0.22][:8] or rows[:5]
        relegation_candidates = sorted(rows, key=lambda row: (-float(row.relegation_probability), -row.predicted_rank, -row.rank))
        relegation_candidates = [row for row in relegation_candidates if float(row.relegation_probability) >= 0.22][:8] or rows[-5:]
        phase = str(summary.phase if summary else "early")
        result[level] = {
            "title": normalized_set(title_candidates),
            "promotion": normalized_set(promotion_candidates) if level != "超级" else set(),
            "relegation": normalized_set(relegation_candidates),
            "phase": phase,
            "critical": phase in {"late", "run_in", "final"},
        }
    return result


def _upcoming_prediction_lines(db: Session, focus_teams: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for level in LEAGUE_LEVELS:
        roles = focus_teams.get(level, {})
        if not roles.get("critical"):
            continue
        matches = db.query(Match).filter(
            Match.level == level,
            Match.status.in_(("scheduled", "postponed")),
            Match.home_score.is_(None),
            Match.away_score.is_(None),
        ).order_by(Match.round_no, Match.id).all()
        if not matches:
            continue
        next_round = min(int(match.round_no or 0) for match in matches)
        for match in matches:
            if int(match.round_no or 0) != next_round:
                continue
            teams = {
                match_service._normalize_team_lookup_name(str(match.home_team_name or "")),
                match_service._normalize_team_lookup_name(str(match.away_team_name or "")),
            }
            label = ""
            if teams & roles.get("title", set()):
                label = "争冠关键战"
            elif teams & roles.get("promotion", set()):
                label = "升级关键战"
            elif teams & roles.get("relegation", set()):
                label = "保级关键战"
            if label:
                lines.append(f"【{label}】{level}第{next_round}轮｜{match.home_team_name} vs {match.away_team_name}")
    return lines[:6]


def _winner_and_loser(match: Match | CupMatch) -> tuple[str, str]:
    home_score = int(match.home_score or 0)
    away_score = int(match.away_score or 0)
    if home_score == away_score or str(match.status) == "double_forfeit":
        return "", ""
    if home_score > away_score:
        return str(match.home_team_name or ""), str(match.away_team_name or "")
    return str(match.away_team_name or ""), str(match.home_team_name or "")


def _focus_score(
    match: Match | CupMatch,
    *,
    level: str | None,
    stats: list[dict[str, Any]],
    power_values: dict[str, float],
    focus_teams: dict[str, dict[str, Any]],
) -> tuple[int, list[str]]:
    score = 0
    tags: list[str] = []
    teams = {
        match_service._normalize_team_lookup_name(str(match.home_team_name or "")),
        match_service._normalize_team_lookup_name(str(match.away_team_name or "")),
    }
    roles = focus_teams.get(str(level or ""), {})
    critical = bool(roles.get("critical"))
    if teams & roles.get("title", set()):
        score += 105 if critical else 80
        tags.append("争冠关键战" if critical else "争冠")
    if teams & roles.get("promotion", set()):
        score += 85 if critical else 60
        tags.append("升级关键战" if critical else "升级")
    if teams & roles.get("relegation", set()):
        score += 90 if critical else 65
        tags.append("保级关键战" if critical else "保级")

    max_goals = max((int(row.get("goals") or 0) for row in stats), default=0)
    if max_goals >= 3:
        score += 100
        tags.append("帽子戏法")

    home_score = int(match.home_score or 0)
    away_score = int(match.away_score or 0)
    margin = abs(home_score - away_score)
    total_goals = home_score + away_score
    if margin >= 4:
        score += 85
        tags.append("大胜")
    elif margin >= 3:
        score += 55
        tags.append("大比分")
    if total_goals >= 7:
        score += 75
        tags.append("进球大战")

    winner, loser = _winner_and_loser(match)
    if winner in power_values and loser in power_values and power_values[loser] - power_values[winner] >= 2.5:
        score += 95
        tags.append("以下克上")
    return score, list(dict.fromkeys(tags))


def _score_ticket(match: Match | CupMatch, label: str) -> str:
    return (
        f"{label} {match.home_team_name} {int(match.home_score or 0)}:"
        f"{int(match.away_score or 0)} {match.away_team_name}"
    )


def _series_summary(stories: list[dict[str, Any]]) -> str:
    if len(stories) < 2:
        return ""
    wins: dict[str, int] = defaultdict(int)
    draws = 0
    for story in stories:
        winner, _loser = _winner_and_loser(story["match"])
        if winner:
            wins[winner] += 1
        else:
            draws += 1
    if len(wins) == 1 and next(iter(wins.values())) == len(stories):
        return f"{next(iter(wins))} 两战全胜。"
    if len(wins) == 2 and all(value == 1 for value in wins.values()) and draws == 0:
        return "双方各取一胜。"
    if not wins:
        return "两回合均以平局收场。"
    ordered = sorted(wins.items(), key=lambda item: (-item[1], item[0]))
    if len(ordered) == 1:
        return f"{ordered[0][0]} 在两回合中取得 {ordered[0][1]} 场胜利。"
    return "两回合各有得失。"


def _leg_narrative(story: dict[str, Any], index: int) -> tuple[str, str]:
    match = story["match"]
    prefix = "首回合" if index == 0 else "次回合" if index == 1 else f"第{index + 1}场"
    home_score = int(match.home_score or 0)
    away_score = int(match.away_score or 0)
    status = str(match.status or "")
    if status == "double_forfeit":
        return "", f"{prefix}双方均被判负"
    if home_score == away_score:
        if home_score == 0:
            return "", f"{prefix} 0:0 互交白卷"
        if home_score + away_score >= 6:
            return "", f"{prefix} {home_score}:{away_score} 上演进球大战后战平"
        return "", f"{prefix} {home_score}:{away_score} 握手言和"

    winner, _loser = _winner_and_loser(match)
    winner_is_home = winner == str(match.home_team_name or "")
    winner_score = home_score if winner_is_home else away_score
    loser_score = away_score if winner_is_home else home_score
    venue = "主场" if winner_is_home else "反客为主"
    category = _match_category(match)
    if category == "forfeit":
        return winner, f"{prefix}{venue}因比赛判定获胜"
    tone = {
        "clean_sheet_rout": "零封横扫，把对手的进球栏牢牢锁死",
        "high_scoring_win": "赢下进球大战，在火力对轰中笑到最后",
        "big_win": "大比分重创对手",
        "narrow_win": "一球险胜，把胜负差距压到最细",
        "regular_win": "力克对手，把效率写成胜果",
    }.get(category, "取胜")
    return winner, f"{prefix}{venue}以 {winner_score}:{loser_score} {tone}"


def _single_match_narrative(story: dict[str, Any]) -> str:
    winner, clause = _leg_narrative(story, 0)
    detail = clause.removeprefix("首回合")
    return f"{winner}{detail}。".strip() if winner else f"{detail}。".strip()


def _series_template_context(stories: list[dict[str, Any]]) -> tuple[str, dict[str, Any], str]:
    teams = sorted({str(story["match"].home_team_name or "") for story in stories} | {str(story["match"].away_team_name or "") for story in stories})
    if len(teams) < 2:
        return "", {}, ""
    team_a, team_b = teams[:2]
    aggregate = {team_a: 0, team_b: 0}
    legs = [_leg_narrative(story, index) for index, story in enumerate(stories[:2])]
    wins: dict[str, int] = defaultdict(int)
    for story in stories[:2]:
        match = story["match"]
        aggregate[str(match.home_team_name or "")] = aggregate.get(str(match.home_team_name or ""), 0) + int(match.home_score or 0)
        aggregate[str(match.away_team_name or "")] = aggregate.get(str(match.away_team_name or ""), 0) + int(match.away_score or 0)
        winner, _loser = _winner_and_loser(match)
        if winner:
            wins[winner] += 1
    first_winner, first_clause = legs[0]
    second_winner, second_clause = legs[1]
    first_leg = f"{first_winner}{first_clause}" if first_winner else first_clause
    second_leg = f"{second_winner}{second_clause}" if second_winner else second_clause
    winner = ""
    loser = ""
    if first_winner and first_winner == second_winner:
        category = "series_sweep"
        winner = first_winner
    elif first_winner and second_winner:
        category = "series_split"
    elif not first_winner and not second_winner:
        category = "series_draws"
    else:
        category = "series_unbeaten"
        winner = first_winner or second_winner
    if winner:
        loser = team_b if winner == team_a else team_a
        aggregate_score = f"{aggregate.get(winner, 0)}:{aggregate.get(loser, 0)}"
    else:
        aggregate_score = f"{aggregate.get(team_a, 0)}:{aggregate.get(team_b, 0)}"
    context = {
        "winner": winner,
        "loser": loser,
        "team_a": team_a,
        "team_b": team_b,
        "aggregate_score": aggregate_score,
        "series_goals": sum(aggregate.values()),
        "first_leg": first_leg,
        "second_leg": second_leg,
    }
    seed = "series:" + ":".join(str(int(story["match"].id or 0)) for story in stories[:2])
    return category, context, seed


def _series_narrative(stories: list[dict[str, Any]], pool: dict[str, list[Any]]) -> str:
    if len(stories) < 2:
        return ""
    category, context, seed = _series_template_context(stories)
    rendered = _render_template(pool, category, context, seed) if category else ""
    if rendered:
        return rendered
    legs = [_leg_narrative(story, index) for index, story in enumerate(stories)]
    if len(legs) != 2:
        return _series_summary(stories)
    first_winner, first_clause = legs[0]
    second_winner, second_clause = legs[1]
    if first_winner and first_winner == second_winner:
        return f"{first_winner}两战全胜：{first_clause}，{second_clause}，完成双杀。"
    if first_winner and second_winner:
        return f"{first_winner}{first_clause}；{second_winner}{second_clause}，双方各取一胜。"
    if not first_winner and not second_winner:
        return f"两回合均战平：{first_clause}，{second_clause}。"
    unbeaten = first_winner or second_winner
    return f"{unbeaten}两回合保持不败：{first_clause}，{second_clause}。"


def _story_highlights(stories: list[dict[str, Any]], limit: int = 2) -> list[str]:
    highlights: list[str] = []
    highlighted_players: set[str] = set()
    ordered = sorted(stories, key=lambda story: (-int(story.get("focus_score") or 0), int(story.get("sort_order") or 0)))
    for story in ordered:
        for key in ("player_phrase", "power_phrase"):
            value = str(story.get(key) or "").strip()
            player_name = str(story.get("highlight_player") or "").strip() if key == "player_phrase" else ""
            if player_name and player_name in highlighted_players:
                continue
            if value and value not in highlights:
                highlights.append(value)
                if player_name:
                    highlighted_players.add(player_name)
            if len(highlights) >= limit:
                return highlights
    return highlights


def _group_story_line(stories: list[dict[str, Any]], pool: dict[str, list[Any]]) -> str:
    first = stories[0]
    teams = sorted({str(first["match"].home_team_name or ""), str(first["match"].away_team_name or "")})
    tickets = "；".join(story["ticket"] for story in stories)
    best = max(stories, key=lambda story: (story["focus_score"], -story["sort_order"]))
    if len(stories) >= 2:
        narrative = _series_narrative(stories, pool)
        highlights = _story_highlights(stories, 2)
    else:
        narrative = ""
        highlights = [" ".join(
            item for item in (
                str(best.get("lead") or "").strip(),
                str(best.get("player_phrase") or "").strip(),
                str(best.get("power_phrase") or "").strip(),
            ) if item
        )]
    suffix = " ".join(item for item in (narrative, *highlights) if item)
    return f"{first['competition_label']}｜{teams[0]} vs {teams[1]}：{tickets}。{suffix}".strip()


def _group_focus_line(stories: list[dict[str, Any]], tags: list[str], pool: dict[str, list[Any]]) -> str:
    first = stories[0]
    teams = sorted({str(first["match"].home_team_name or ""), str(first["match"].away_team_name or "")})
    tickets = "；".join(story["ticket"] for story in stories)
    tag_text = "·".join(tags[:3]) or "焦点"
    best = max(stories, key=lambda story: (story["focus_score"], -story["sort_order"]))
    narrative = _series_narrative(stories, pool) if len(stories) >= 2 else _single_match_narrative(best)
    highlights = _story_highlights(stories, 2)
    suffix = " ".join(item for item in (narrative, *highlights) if item)
    return f"【{tag_text}】{first['competition_label']}｜{teams[0]} vs {teams[1]}：{tickets}。{suffix}".strip()


def _group_match_stories(stories: list[dict[str, Any]], pool: dict[str, list[Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for story in stories:
        match = story["match"]
        teams = sorted((str(match.home_team_name or ""), str(match.away_team_name or "")))
        grouped[(story["kind"], story["competition_key"], teams[0], teams[1])].append(story)
    result: list[dict[str, Any]] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda story: (story["sort_order"], int(story["match"].id or 0)))
        tags = list(dict.fromkeys(tag for story in ordered for tag in story["tags"]))
        result.append({
            "line": _group_story_line(ordered, pool),
            "focus_line": _group_focus_line(ordered, tags, pool),
            "focus_score": sum(story["focus_score"] for story in ordered) + (25 if len(ordered) > 1 and tags else 0),
            "tags": tags,
            "sort_order": min(story["sort_order"] for story in ordered),
            "kind": ordered[0]["kind"],
        })
    return sorted(result, key=lambda item: (item["kind"] != "league", item["sort_order"], item["line"]))


def _select_focus_stories(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        candidates,
        key=lambda item: (-int(item["focus_score"]), item["sort_order"], item["line"]),
    )
    selected: list[dict[str, Any]] = []
    for priority_tag in ("争冠", "升级", "保级"):
        priority_story = next((story for story in ranked if any(priority_tag in tag for tag in story["tags"]) and story not in selected), None)
        if priority_story:
            selected.append(priority_story)
    for story in ranked:
        if story not in selected:
            selected.append(story)
        if len(selected) >= MAX_FOCUS_STORIES:
            break
    return sorted(selected[:MAX_FOCUS_STORIES], key=lambda item: (-int(item["focus_score"]), item["sort_order"], item["line"]))


def _extract_focus_content(content: str) -> str:
    lines = [line.rstrip() for line in str(content or "").splitlines()]
    non_empty = [line for line in lines if line.strip()]
    overview = next((line for line in non_empty if not line.strip().startswith("【")), "今日暂无可播报内容。")
    start = next((index for index, line in enumerate(lines) if line.strip() == "【焦点头版】"), None)
    if start is None:
        if not non_empty:
            return overview
        return "\n".join([overview, "", "【焦点头版】", *non_empty]).strip()
    selected = [overview, "", "【焦点头版】"]
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped.startswith("【") and stripped.endswith("】"):
            break
        if stripped:
            selected.append(line)
    return "\n".join(selected).strip()


def _focus_line_count(content: str) -> int:
    active = False
    count = 0
    for raw_line in str(content or "").splitlines():
        line = raw_line.strip()
        if line == "【焦点头版】":
            active = True
            continue
        if active and line.startswith("【"):
            break
        if active and line:
            count += 1
    return count


def build_daily_report(db: Session, report_date: str | date | None = None) -> DailyReportResponse:
    selected_date = _parse_report_date(report_date)
    start, end = _date_bounds(selected_date)
    pool = _template_pool(db)
    power_values = _power_values(db)
    focus_teams = _focus_teams(db)

    league_matches = db.query(Match).filter(
        Match.updated_at >= start,
        Match.updated_at < end,
        Match.status.in_(PLAYED_MATCH_STATUSES),
        Match.home_score.is_not(None),
        Match.away_score.is_not(None),
    ).order_by(Match.level, Match.round_no, Match.id).all()
    cup_matches = db.query(CupMatch).filter(
        CupMatch.updated_at >= start,
        CupMatch.updated_at < end,
        CupMatch.status == "played",
        CupMatch.home_score.is_not(None),
        CupMatch.away_score.is_not(None),
    ).order_by(CupMatch.competition, CupMatch.stage, CupMatch.slot_no).all()
    match_ids = [int(match.id) for match in league_matches]
    events_by_match: dict[int, list[MatchPlayerEvent]] = defaultdict(list)
    if match_ids:
        for event in db.query(MatchPlayerEvent).filter(MatchPlayerEvent.match_id.in_(match_ids)).all():
            events_by_match[int(event.match_id)].append(event)

    match_stories: list[dict[str, Any]] = []
    total_goals = 0
    for match in league_matches:
        context = _match_context(match, f"{match.level}联赛", f"第{int(match.round_no)}轮")
        seed = f"league:{match.id}:{selected_date.isoformat()}"
        lead = _render_template(pool, _match_category(match), context, seed)
        stats = _event_stats(events_by_match.get(int(match.id), []))
        player, highlight_player = _player_highlight(pool, stats, context, seed)
        power = _power_phrase(pool, context, power_values, seed)
        focus_score, tags = _focus_score(
            match,
            level=str(match.level),
            stats=stats,
            power_values=power_values,
            focus_teams=focus_teams,
        )
        match_stories.append({
            "kind": "league",
            "competition_key": str(match.level),
            "competition_label": f"{match.level}联赛",
            "match": match,
            "ticket": _score_ticket(match, f"第{int(match.round_no)}轮"),
            "lead": lead,
            "player_phrase": player,
            "highlight_player": highlight_player,
            "power_phrase": power,
            "focus_score": focus_score,
            "tags": tags,
            "sort_order": int(match.round_no or 0),
        })
        total_goals += int(match.home_score or 0) + int(match.away_score or 0)

    for match in cup_matches:
        definition = cup_service.CUP_DEFINITIONS.get(str(match.competition), {})
        competition = str(definition.get("title") or match.competition)
        stage = _cup_stage_label(match)
        context = _match_context(match, competition, stage)
        seed = f"cup:{match.id}:{selected_date.isoformat()}"
        lead = _render_template(pool, _match_category(match), context, seed)
        power = _power_phrase(pool, context, power_values, seed)
        focus_score, tags = _focus_score(
            match,
            level=None,
            stats=[],
            power_values=power_values,
            focus_teams=focus_teams,
        )
        match_stories.append({
            "kind": "cup",
            "competition_key": str(match.competition),
            "competition_label": competition,
            "match": match,
            "ticket": _score_ticket(match, stage),
            "lead": lead,
            "player_phrase": "",
            "highlight_player": "",
            "power_phrase": power,
            "focus_score": focus_score,
            "tags": tags,
            "sort_order": int(match.slot_no or 0),
        })
        total_goals += int(match.home_score or 0) + int(match.away_score or 0)

    grouped_stories = _group_match_stories(match_stories, pool)
    focus_candidates = [story for story in grouped_stories if int(story["focus_score"]) >= 65]
    focus_stories = _select_focus_stories(focus_candidates)
    focus_line_set = {story["line"] for story in focus_stories}
    regular_stories = [story for story in grouped_stories if story["line"] not in focus_line_set]

    suspensions = db.query(PlayerSuspensionRecord).filter(
        PlayerSuspensionRecord.updated_at >= start,
        PlayerSuspensionRecord.updated_at < end,
    ).order_by(PlayerSuspensionRecord.level, PlayerSuspensionRecord.team_name, PlayerSuspensionRecord.player_name).all()
    suspension_lines = [
        f"{row.level}｜{row.team_name}：{row.player_name}（{_suspension_label(row)}）"
        for row in suspensions[:8]
    ]
    if len(suspensions) > 8:
        suspension_lines.append(f"另有 {len(suspensions) - 8} 条伤停状态更新，可前往主站查看完整名单。")

    match_count = len(league_matches) + len(cup_matches)
    overview = f"今日共更新 {match_count} 场比赛，产生 {total_goals} 粒进球。" if match_count else "今日暂无新增赛果。"
    if suspensions:
        overview += f" 同时有 {len(suspensions)} 条伤停信息发生更新。"
    lines = [overview]
    if focus_stories:
        lines.extend(("", "【焦点头版】", *(story["line"] for story in focus_stories)))
    if regular_stories:
        lines.extend(("", "【常规战报】", *(story["line"] for story in regular_stories)))
    if suspension_lines:
        lines.extend(("", "【伤停动态】", *suspension_lines))
    prediction_lines = _upcoming_prediction_lines(db, focus_teams)
    if prediction_lines:
        lines.extend(("", "【排名预测关键战】", *prediction_lines))
    power_lines = _upcoming_power_lines(db, power_values)
    if power_lines:
        lines.extend(("", "【下一轮战力看点】", *power_lines))
    content = team_name_service.localize_team_names_in_text("\n".join(lines).strip())
    focus_content_lines = [overview]
    if focus_stories:
        focus_content_lines.extend(("", "【焦点头版】", *(story["focus_line"] for story in focus_stories)))
    focus_content = team_name_service.localize_team_names_in_text("\n".join(focus_content_lines).strip())
    title = f"HEIGO 联赛日报｜{selected_date.month}月{selected_date.day}日"
    fingerprint = _fingerprint(selected_date, title, content)
    now = datetime.now()
    return DailyReportResponse(
        report_date=selected_date.isoformat(),
        title=title,
        content=content,
        focus_content=focus_content,
        image_url=_report_image_url(selected_date.isoformat(), fingerprint),
        status="generated",
        fingerprint=fingerprint,
        match_count=match_count,
        fixture_group_count=len(grouped_stories),
        focus_count=len(focus_stories),
        league_match_count=len(league_matches),
        cup_match_count=len(cup_matches),
        goal_count=total_goals,
        suspension_count=len(suspensions),
        generated_at=now,
    )


def _payload_from_response(report: DailyReportResponse) -> dict[str, Any]:
    return {
        "match_count": report.match_count,
        "league_match_count": report.league_match_count,
        "cup_match_count": report.cup_match_count,
        "goal_count": report.goal_count,
        "suspension_count": report.suspension_count,
        "fixture_group_count": report.fixture_group_count,
        "focus_count": report.focus_count,
        "focus_content": report.focus_content,
    }


def _row_response(row: DailyReport, *, localize_team_names: bool = False) -> DailyReportResponse:
    try:
        payload = json.loads(row.payload_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    stored_fingerprint = str(row.fingerprint or "")
    content = row.content or ""
    if localize_team_names:
        content = team_name_service.localize_team_names_in_text(content)
    stored_focus_content = str(payload.get("focus_content") or "").strip()
    if localize_team_names:
        stored_focus_content = team_name_service.localize_team_names_in_text(stored_focus_content)
    focus_content = stored_focus_content or _extract_focus_content(content)
    fingerprint = _fingerprint(date.fromisoformat(row.report_date), row.title, content) if localize_team_names else stored_fingerprint
    return DailyReportResponse(
        report_date=row.report_date,
        title=row.title,
        content=content,
        focus_content=focus_content,
        image_url=_report_image_url(row.report_date, fingerprint),
        status=row.status if row.status in REPORT_STATUSES else "draft",
        fingerprint=fingerprint,
        match_count=int(payload.get("match_count") or 0),
        fixture_group_count=int(payload.get("fixture_group_count") or 0),
        focus_count=int(payload.get("focus_count") or 0),
        league_match_count=int(payload.get("league_match_count") or 0),
        cup_match_count=int(payload.get("cup_match_count") or 0),
        goal_count=int(payload.get("goal_count") or 0),
        suspension_count=int(payload.get("suspension_count") or 0),
        generated_at=row.generated_at or row.created_at or datetime.now(),
        published_at=row.published_at,
        published_by=row.published_by,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


def get_public_report(db: Session, report_date: str | date | None = None) -> DailyReportResponse:
    selected_date = _parse_report_date(report_date)
    row = db.query(DailyReport).filter(
        DailyReport.report_date == selected_date.isoformat(),
        DailyReport.status == "published",
    ).first()
    if row:
        return _row_response(row, localize_team_names=True)
    cache_key = selected_date.isoformat()
    cached = _AUTO_REPORT_CACHE.get(cache_key)
    now = monotonic_time.monotonic()
    if cached and now - cached[0] < AUTO_REPORT_CACHE_TTL_SECONDS:
        return cached[1].model_copy(deep=True)
    report = build_daily_report(db, selected_date)
    _AUTO_REPORT_CACHE[cache_key] = (now, report.model_copy(deep=True))
    return report


def get_workspace_report(
    db: Session,
    identity: WorkspaceIdentityResponse,
    report_date: str | date | None = None,
) -> DailyReportResponse:
    _require_daily_report_manager(identity)
    selected_date = _parse_report_date(report_date)
    row = db.query(DailyReport).filter(DailyReport.report_date == selected_date.isoformat()).first()
    return _row_response(row) if row else build_daily_report(db, selected_date)


def generate_workspace_report(
    db: Session,
    identity: WorkspaceIdentityResponse,
    report_date: str | date | None = None,
) -> DailyReportResponse:
    operator = _require_daily_report_manager(identity)
    generated = build_daily_report(db, report_date)
    row = db.query(DailyReport).filter(DailyReport.report_date == generated.report_date).first()
    now = datetime.now()
    if not row:
        row = DailyReport(report_date=generated.report_date, created_by=operator, created_at=now)
        db.add(row)
    row.title = generated.title
    row.content = generated.content
    row.payload_json = json.dumps(_payload_from_response(generated), ensure_ascii=False)
    row.status = "draft"
    row.fingerprint = generated.fingerprint
    row.generated_at = generated.generated_at
    row.published_at = None
    row.published_by = None
    row.updated_by = operator
    row.updated_at = now
    _audit(db, operator, "generate_daily_report", f"生成 {generated.report_date} 联赛日报", {"report_date": generated.report_date, "match_count": generated.match_count})
    db.commit()
    db.refresh(row)
    _AUTO_REPORT_CACHE.pop(generated.report_date, None)
    return _row_response(row)


def update_workspace_report(
    db: Session,
    identity: WorkspaceIdentityResponse,
    report_date: str,
    request: DailyReportUpdateRequest,
) -> DailyReportResponse:
    operator = _require_daily_report_manager(identity)
    selected_date = _parse_report_date(report_date)
    title = str(request.title or "").strip()
    content = str(request.content or "").strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="日报标题和正文不能为空")
    if len(title) > 120 or len(content) > 12000:
        raise HTTPException(status_code=400, detail="日报标题或正文过长")
    row = db.query(DailyReport).filter(DailyReport.report_date == selected_date.isoformat()).first()
    if not row:
        generated = build_daily_report(db, selected_date)
        row = DailyReport(
            report_date=selected_date.isoformat(),
            payload_json=json.dumps(_payload_from_response(generated), ensure_ascii=False),
            generated_at=generated.generated_at,
            created_by=operator,
            created_at=datetime.now(),
        )
        db.add(row)
    now = datetime.now()
    row.title = title
    row.content = content
    try:
        payload = json.loads(row.payload_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    payload["focus_content"] = _extract_focus_content(content)
    payload["focus_count"] = _focus_line_count(content)
    row.payload_json = json.dumps(payload, ensure_ascii=False)
    row.status = "published" if request.publish else "draft"
    row.fingerprint = _fingerprint(selected_date, title, content)
    row.published_at = now if request.publish else None
    row.published_by = operator if request.publish else None
    row.updated_by = operator
    row.updated_at = now
    action = "publish_daily_report" if request.publish else "save_daily_report_draft"
    label = "发布" if request.publish else "保存"
    _audit(db, operator, action, f"{label} {selected_date.isoformat()} 联赛日报", {"report_date": selected_date.isoformat(), "fingerprint": row.fingerprint})
    db.commit()
    db.refresh(row)
    _AUTO_REPORT_CACHE.pop(selected_date.isoformat(), None)
    return _row_response(row)
