from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Player, Team
from repositories.player_repository import get_player_by_uid
from repositories.team_repository import get_other_team_by_name, get_team_by_name
from repositories.transfer_log_repository import update_player_uid_references
from team_links import get_team_players
from services.admin_common import LogWriter, require_admin
from services.league_service import (
    PERSISTED_TEAM_STAT_SCOPES,
    TEAM_STAT_SCOPE_WAGE,
    persist_with_team_stats,
    refresh_player_financials,
)


def consume_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    player = get_player_by_uid(db, request.player_uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")

    old_ca, old_pa = player.ca, player.pa
    player.ca = max(1, player.ca + request.ca_change)
    player.pa = max(1, player.pa + request.pa_change)
    refresh_player_financials(player, db)

    from services.league_service import create_transfer_log

    create_transfer_log(
        db,
        player_uid=player.uid,
        player_name=player.name,
        from_team=player.team_name,
        to_team=player.team_name,
        from_team_id=player.team_id,
        to_team_id=player.team_id,
        operation="消费",
        operator=admin,
        notes=request.notes or "",
        ca_change=request.ca_change,
        pa_change=request.pa_change,
    )
    persist_with_team_stats(
        db,
        affected_team_ids={player.team_id},
        stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
    )

    log_detail = f"球员 {player.name}(UID:{player.uid}) CA:{old_ca}→{player.ca}, PA:{old_pa}→{player.pa}"
    write_to_log("消费", log_detail, admin)
    return {"success": True, "message": f"{player.name} CA: {old_ca}→{player.ca}, PA: {old_pa}→{player.pa}"}


def rejuvenate_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    player = get_player_by_uid(db, request.player_uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")

    old_age = player.age
    player.age = max(15, player.age - request.age_change)
    refresh_player_financials(player, db)

    from services.league_service import create_transfer_log

    create_transfer_log(
        db,
        player_uid=player.uid,
        player_name=player.name,
        from_team=player.team_name,
        to_team=player.team_name,
        from_team_id=player.team_id,
        to_team_id=player.team_id,
        operation="返老",
        operator=admin,
        notes=request.notes or "",
        age_change=request.age_change,
    )
    persist_with_team_stats(
        db,
        affected_team_ids={player.team_id},
        stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
    )

    log_detail = f"球员 {player.name}(UID:{player.uid}) 年龄:{old_age}→{player.age}"
    write_to_log("返老", log_detail, admin)
    return {"success": True, "message": f"{player.name} 年龄: {old_age}→{player.age}"}


def batch_consume(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    results = []
    success_count = 0
    affected_team_ids: set[int | None] = set()

    from services.league_service import create_transfer_log

    for item in request.items:
        player = get_player_by_uid(db, item.uid)
        if not player:
            results.append({"uid": item.uid, "success": False, "message": "球员不存在"})
            continue

        old_ca, old_pa = player.ca, player.pa
        player.ca = max(1, player.ca + item.ca_change)
        player.pa = max(1, player.pa + item.pa_change)
        refresh_player_financials(player, db)
        affected_team_ids.add(player.team_id)
        create_transfer_log(
            db,
            player_uid=player.uid,
            player_name=player.name,
            from_team=player.team_name,
            to_team=player.team_name,
            from_team_id=player.team_id,
            to_team_id=player.team_id,
            operation="批量消费",
            operator=admin,
            notes=item.notes or "",
            ca_change=item.ca_change,
            pa_change=item.pa_change,
        )
        results.append({"uid": item.uid, "success": True, "message": f"{player.name}: CA{old_ca}→{player.ca}, PA{old_pa}→{player.pa}"})
        success_count += 1

    if success_count:
        persist_with_team_stats(
            db,
            affected_team_ids=affected_team_ids,
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
        )

    log_detail = f"批量消费 {success_count}/{len(request.items)} 条记录成功"
    write_to_log("批量消费", log_detail, admin)
    return {"success": True, "results": results, "success_count": success_count}


def update_team_info(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    team = get_team_by_name(db, request.team_name)
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在")

    old_manager = team.manager
    old_name = team.name
    old_notes = team.notes
    old_level = team.level

    if request.manager is not None:
        team.manager = request.manager
    if request.name is not None:
        existing = get_other_team_by_name(db, request.name, team.id)
        if existing:
            raise HTTPException(status_code=400, detail="球队名已存在")
        players = get_team_players(db, team)
        for player in players:
            player.team_id = team.id
            player.team_name = request.name
        team.name = request.name
    if request.notes is not None:
        team.notes = request.notes
    if request.level is not None:
        team.level = request.level

    affected_scopes = set()
    if request.level is not None and request.level != old_level:
        affected_scopes.add(TEAM_STAT_SCOPE_WAGE)
    if request.notes is not None and request.notes != old_notes:
        affected_scopes.add(TEAM_STAT_SCOPE_WAGE)

    if affected_scopes:
        persist_with_team_stats(db, affected_team_ids={team.id}, stat_scopes=affected_scopes)
    else:
        db.commit()

    changes = []
    if request.manager is not None and request.manager != old_manager:
        changes.append(f"主教: {old_manager} → {request.manager}")
    if request.name is not None and request.name != old_name:
        changes.append(f"队名: {old_name} → {request.name}")
    if request.notes is not None and request.notes != old_notes:
        changes.append("备注已更新")
    if request.level is not None and request.level != old_level:
        changes.append(f"级别: {old_level} → {request.level}")

    if not changes:
        changes.append("无字段变化")

    log_detail = f"球队 {old_name} 信息修改: {', '.join(changes)}"
    write_to_log("球队修改", log_detail, admin)
    return {"success": True, "message": f"球队信息已更新: {', '.join(changes)}"}


def update_player_info(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    player = get_player_by_uid(db, request.uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")

    old_name = player.name
    old_position = player.position
    old_nationality = player.nationality
    old_age = player.age

    changes = []
    if request.name is not None and request.name != player.name:
        player.name = request.name
        changes.append(f"姓名：{old_name} → {request.name}")
    if request.position is not None and request.position != player.position:
        player.position = request.position
        changes.append(f"位置：{old_position} → {request.position}")
    if request.nationality is not None and request.nationality != player.nationality:
        player.nationality = request.nationality
        changes.append(f"国籍：{old_nationality} → {request.nationality}")
    if request.age is not None and request.age != player.age:
        player.age = request.age
        changes.append(f"年龄：{old_age} → {request.age}")

    if request.position is not None or request.age is not None:
        refresh_player_financials(player, db)
        persist_with_team_stats(
            db,
            affected_team_ids={player.team_id},
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
        )
    else:
        db.commit()

    if not changes:
        changes.append("无字段变化")

    log_detail = f"球员 {old_name}(UID:{request.uid}) 修改: {', '.join(changes)}"
    write_to_log("球员修改", log_detail, admin)
    return {"success": True, "message": f"{player.name} 已更新: {', '.join(changes)}"}


def update_player_uid(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    player = get_player_by_uid(db, request.old_uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")

    existing_player = get_player_by_uid(db, request.new_uid)
    if existing_player:
        raise HTTPException(status_code=400, detail=f"UID {request.new_uid} 已被使用")

    old_uid = player.uid
    player.uid = request.new_uid
    update_player_uid_references(db, old_uid, request.new_uid)
    db.commit()

    log_detail = f"球员 {player.name} UID修改: {old_uid} → {request.new_uid}"
    write_to_log("UID修改", log_detail, admin)
    return {"success": True, "message": f"{player.name} 的UID已从 {old_uid} 更新为 {request.new_uid}"}


def undo_roster_operation(db: Session, log: TransferLog, player: Player | None) -> tuple[bool, str, set[str]]:
    if log.operation in ["消费", "批量消费"]:
        if not player:
            raise HTTPException(status_code=404, detail="球员不存在")
        if log.ca_change:
            player.ca = max(1, player.ca - log.ca_change)
        if log.pa_change:
            player.pa = max(1, player.pa - log.pa_change)
        refresh_player_financials(player, db)
        return True, f"CA/PA 回滚到 {player.ca}/{player.pa}", set(PERSISTED_TEAM_STAT_SCOPES)

    if log.operation == "返老":
        if not player:
            raise HTTPException(status_code=404, detail="球员不存在")
        if log.age_change:
            player.age = player.age + log.age_change
        refresh_player_financials(player, db)
        return True, f"年龄回滚到 {player.age}", set(PERSISTED_TEAM_STAT_SCOPES)

    return False, "", set()
