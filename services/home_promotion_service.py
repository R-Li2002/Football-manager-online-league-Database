from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import CupMatch, HomePromotion, Match, OperationAudit, Team
from schemas_read import HomePromotionResponse, WorkspaceIdentityResponse
from schemas_write import HomePromotionUpsertRequest
from services.cup_service import CUP_DEFINITIONS


BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
VALID_ROOT_TAB_TARGETS = {"home", "overview", "players", "team", "coaches", "database", "competition"}
VALID_DATABASE_SUBTABS = {"search", "candidates", "power", "tactics", "leaderboard"}
VALID_COMPETITION_SUBTABS = {"standings", "schedule", "playerRankings", "suspensions"}
VALID_COMPETITION_LEVELS = {"超级", "甲级", "乙级", "冠军杯", "联盟杯", "无铭剑杯"}
PROMOTION_THEMES = {"violet", "blue", "green", "gold", "rose", "neutral"}
LEAGUE_LEVELS = ("超级", "甲级", "乙级")
LEAGUE_RESULT_STATUSES = {"played", "home_forfeit", "away_forfeit", "double_forfeit"}


def _require_full_admin(identity: WorkspaceIdentityResponse) -> str:
    if not identity.is_full_admin:
        raise HTTPException(status_code=403, detail="只有完整管理员可以管理主页宣传")
    return identity.username


def _clean_optional(value: str | None, limit: int, label: str) -> str | None:
    clean = str(value or "").strip()
    if len(clean) > limit:
        raise HTTPException(status_code=400, detail=f"{label}不能超过 {limit} 个字符")
    return clean or None


def _business_now() -> datetime:
    """Return the league's wall-clock time for naive SQLite schedule fields."""
    return datetime.now(BUSINESS_TIMEZONE).replace(tzinfo=None)


def _normalize_tab_target(value: str | None) -> str | None:
    target = _clean_optional(value, 300, "按钮目标")
    if target == "competition:rankings":
        return "competition:playerRankings"
    return target


def _is_valid_tab_target(target: str) -> bool:
    parts = target.split(":")
    if not parts or parts[0] not in VALID_ROOT_TAB_TARGETS:
        return False
    if len(parts) == 1:
        return True
    if parts[0] == "database":
        return len(parts) == 2 and parts[1] in VALID_DATABASE_SUBTABS
    if parts[0] != "competition" or len(parts) > 3 or parts[1] not in VALID_COMPETITION_SUBTABS:
        return False
    if len(parts) == 2:
        return True
    level = parts[2]
    if level not in VALID_COMPETITION_LEVELS:
        return False
    return parts[1] in {"standings", "schedule"} or level in LEAGUE_LEVELS


def _validate_request(request: HomePromotionUpsertRequest) -> dict:
    title = str(request.title or "").strip()
    body = str(request.body or "").strip()
    eyebrow = str(request.eyebrow or "").strip() or "HEIGO Broadcast"
    if not title:
        raise HTTPException(status_code=400, detail="宣传标题不能为空")
    if len(title) > 120:
        raise HTTPException(status_code=400, detail="宣传标题不能超过 120 个字符")
    if len(body) > 600:
        raise HTTPException(status_code=400, detail="宣传正文不能超过 600 个字符")
    if len(eyebrow) > 60:
        raise HTTPException(status_code=400, detail="宣传眉题不能超过 60 个字符")
    if request.starts_at and request.ends_at and request.ends_at <= request.starts_at:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    action_label = _clean_optional(request.action_label, 40, "按钮文字")
    action_target = _normalize_tab_target(request.action_target)
    if request.action_kind == "none":
        action_label = None
        action_target = None
    elif not action_label or not action_target:
        raise HTTPException(status_code=400, detail="启用宣传按钮时必须填写按钮文字和目标")
    elif request.action_kind == "tab" and not _is_valid_tab_target(action_target):
        raise HTTPException(status_code=400, detail="不支持的站内页面目标")
    elif request.action_kind == "url" and not action_target.startswith(("/", "https://", "http://")):
        raise HTTPException(status_code=400, detail="链接必须以 /、https:// 或 http:// 开头")
    return {
        "content_type": request.content_type,
        "theme": request.theme,
        "icon": request.icon,
        "eyebrow": eyebrow,
        "title": title,
        "body": body,
        "image_url": _clean_optional(request.image_url, 300, "图片地址"),
        "action_label": action_label,
        "action_kind": request.action_kind,
        "action_target": action_target,
        "display_mode": request.display_mode,
        "is_active": int(bool(request.is_active)),
        "is_pinned": int(bool(request.is_pinned)),
        "is_dismissible": int(bool(request.is_dismissible)),
        "sort_order": max(0, min(9999, int(request.sort_order))),
        "starts_at": request.starts_at,
        "ends_at": request.ends_at,
    }


def _response(row: HomePromotion) -> HomePromotionResponse:
    return HomePromotionResponse.model_validate(row)


def _audit(db: Session, operator: str, action: str, summary: str, details: dict | None = None) -> None:
    db.add(OperationAudit(category="content", action=action, status="success", source="admin_ui", operator=operator, summary=summary, details_json=json.dumps(details or {}, ensure_ascii=False), created_at=datetime.now()))


def list_public_promotions(db: Session) -> list[HomePromotionResponse]:
    now = _business_now()
    rows = (
        db.query(HomePromotion)
        .filter(
            HomePromotion.is_active == 1,
            or_(HomePromotion.starts_at.is_(None), HomePromotion.starts_at <= now),
            or_(HomePromotion.ends_at.is_(None), HomePromotion.ends_at >= now),
        )
        .order_by(HomePromotion.is_pinned.desc(), HomePromotion.sort_order.asc(), HomePromotion.updated_at.desc(), HomePromotion.id.desc())
        .all()
    )
    return [_response(row) for row in rows]


def list_admin_promotions(db: Session, identity: WorkspaceIdentityResponse) -> list[HomePromotionResponse]:
    _require_full_admin(identity)
    rows = db.query(HomePromotion).order_by(HomePromotion.sort_order.asc(), HomePromotion.id.desc()).all()
    return [_response(row) for row in rows]


def create_promotion(db: Session, identity: WorkspaceIdentityResponse, request: HomePromotionUpsertRequest) -> HomePromotionResponse:
    operator = _require_full_admin(identity)
    row = HomePromotion(**_validate_request(request), source_type="custom", created_by=operator, updated_by=operator, created_at=datetime.now(), updated_at=datetime.now())
    db.add(row)
    db.flush()
    _audit(db, operator, "create_home_promotion", f"新增主页宣传：{row.title}", {"promotion_id": row.id})
    db.commit()
    db.refresh(row)
    return _response(row)


def update_promotion(db: Session, identity: WorkspaceIdentityResponse, promotion_id: int, request: HomePromotionUpsertRequest) -> HomePromotionResponse:
    operator = _require_full_admin(identity)
    row = db.query(HomePromotion).filter(HomePromotion.id == promotion_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="主页宣传不存在")
    for key, value in _validate_request(request).items():
        setattr(row, key, value)
    row.updated_by = operator
    row.updated_at = datetime.now()
    _audit(db, operator, "update_home_promotion", f"修改主页宣传：{row.title}", {"promotion_id": row.id})
    db.commit()
    db.refresh(row)
    return _response(row)


def delete_promotion(db: Session, identity: WorkspaceIdentityResponse, promotion_id: int) -> dict[str, str | bool]:
    operator = _require_full_admin(identity)
    row = db.query(HomePromotion).filter(HomePromotion.id == promotion_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="主页宣传不存在")
    title = row.title
    db.delete(row)
    _audit(db, operator, "delete_home_promotion", f"删除主页宣传：{title}", {"promotion_id": promotion_id})
    db.commit()
    return {"success": True, "message": "宣传内容已删除"}


def sync_cup_champions(db: Session, identity: WorkspaceIdentityResponse) -> list[HomePromotionResponse]:
    operator = _require_full_admin(identity)
    created = 0
    updated = 0
    themes = {"champions_cup": "gold", "league_cup": "violet", "wumingjian_cup": "green"}
    for index, (competition, definition) in enumerate(CUP_DEFINITIONS.items()):
        final = db.query(CupMatch).filter(CupMatch.competition == competition, CupMatch.stage == "final", CupMatch.status == "played").order_by(CupMatch.updated_at.desc(), CupMatch.id.desc()).first()
        if not final or not final.winner_team_name:
            continue
        team = db.query(Team).filter(Team.id == final.winner_team_id).first() if final.winner_team_id else None
        source_key = f"{competition}:{final.winner_team_id or final.winner_team_name}"
        row = db.query(HomePromotion).filter(HomePromotion.source_type == "cup_champion", HomePromotion.source_key == source_key).first()
        score = "决赛结果已确认" if final.home_score is None or final.away_score is None else f"决赛 {final.home_score} : {final.away_score}"
        manager = str(team.manager or "").strip() if team else ""
        payload = {
            "content_type": "honor", "theme": themes[competition], "icon": "trophy",
            "eyebrow": f"{definition['title']} · CHAMPION", "title": f"{final.winner_team_name} 荣膺{definition['title']}冠军",
            "body": f"{score}{f' · 主教练 {manager}' if manager else ''}", "image_url": str(team.logo_path or "").strip() if team else None,
            "action_label": "查看夺冠之路", "action_kind": "tab", "action_target": f"competition:standings:{definition['title']}",
            "is_active": 1, "is_pinned": 1, "is_dismissible": 1, "sort_order": 10 + index,
            "updated_by": operator, "updated_at": datetime.now(),
        }
        if row:
            for key, value in payload.items():
                setattr(row, key, value)
            updated += 1
        else:
            db.add(HomePromotion(**payload, source_type="cup_champion", source_key=source_key, created_by=operator, created_at=datetime.now()))
            created += 1
    _audit(db, operator, "sync_cup_champions", f"同步杯赛冠军宣传：新增 {created}，更新 {updated}", {"created": created, "updated": updated})
    db.commit()
    return list_admin_promotions(db, identity)


def sync_league_champions(db: Session, identity: WorkspaceIdentityResponse) -> list[HomePromotionResponse]:
    from services import match_service

    operator = _require_full_admin(identity)
    standings = match_service.get_standings(db)
    created = 0
    updated = 0
    skipped: list[str] = []
    themes = {"超级": "violet", "甲级": "blue", "乙级": "green"}
    for index, level in enumerate(LEAGUE_LEVELS):
        matches = (
            db.query(Match)
            .filter(Match.level == level, Match.round_no >= 1, Match.round_no <= 34)
            .order_by(Match.round_no, Match.id)
            .all()
        )
        rounds = {int(match.round_no) for match in matches}
        level_rows = [row for row in standings.rows if row.level == level]
        schedule_complete = rounds == set(range(1, 35)) and bool(matches) and all(
            match.status in LEAGUE_RESULT_STATUSES
            and match.home_score is not None
            and match.away_score is not None
            for match in matches
        )
        table_complete = bool(level_rows) and all(int(row.played or 0) >= 34 for row in level_rows)
        if not schedule_complete or not table_complete:
            skipped.append(level)
            continue
        champion = next((row for row in level_rows if row.rank == 1), None)
        if not champion:
            skipped.append(level)
            continue
        team = db.query(Team).filter(Team.id == champion.team_id).first() if champion.team_id else None
        season_labels = [str(match.season_label or "").strip() for match in matches if str(match.season_label or "").strip()]
        season_label = max(set(season_labels), key=season_labels.count) if season_labels else "current"
        source_key = f"{level}:{season_label}"
        row = db.query(HomePromotion).filter(HomePromotion.source_type == "league_champion", HomePromotion.source_key == source_key).first()
        manager = str(champion.manager or team.manager or "").strip() if team else str(champion.manager or "").strip()
        payload = {
            "content_type": "honor",
            "theme": themes[level],
            "icon": "trophy",
            "eyebrow": f"{level}联赛 · CHAMPION",
            "title": f"{champion.team_name} 荣膺{level}联赛冠军",
            "body": f"34 轮战罢 · {champion.points} 分 · {champion.wins} 胜 {champion.draws} 平 {champion.losses} 负{f' · 主教练 {manager}' if manager else ''}",
            "image_url": str(team.logo_path or "").strip() if team else None,
            "action_label": "查看最终积分榜",
            "action_kind": "tab",
            "action_target": f"competition:standings:{level}",
            "is_active": 1,
            "is_pinned": 1,
            "is_dismissible": 1,
            "sort_order": 1 + index,
            "updated_by": operator,
            "updated_at": datetime.now(),
        }
        if row:
            for key, value in payload.items():
                setattr(row, key, value)
            updated += 1
        else:
            db.add(HomePromotion(**payload, source_type="league_champion", source_key=source_key, created_by=operator, created_at=datetime.now()))
            created += 1
    _audit(
        db,
        operator,
        "sync_league_champions",
        f"同步联赛冠军宣传：新增 {created}，更新 {updated}，未完成 {len(skipped)}",
        {"created": created, "updated": updated, "skipped_levels": skipped},
    )
    db.commit()
    return list_admin_promotions(db, identity)
