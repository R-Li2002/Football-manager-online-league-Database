from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Player
from repositories.player_repository import get_player_by_uid
from repositories.transfer_log_repository import get_transfer_log_by_id
from team_links import (
    assign_player_team,
    assign_player_team_by_name,
    get_sea_team,
    get_team_by_id,
    get_team_by_name,
)
from services.admin_common import LogWriter, require_admin
from services.league_service import (
    PERSISTED_TEAM_STAT_SCOPES,
    create_transfer_log,
    persist_with_team_stats,
    refresh_player_financials,
)


def transfer_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    player = get_player_by_uid(db, request.player_uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")

    new_team = get_team_by_name(db, request.to_team)
    if not new_team:
        raise HTTPException(status_code=404, detail="目标球队不存在")

    from_team = player.team_name
    from_team_id = player.team_id
    from_team_record = get_team_by_name(db, from_team) if from_team else None
    assign_player_team(player, new_team)

    create_transfer_log(
        db,
        player_uid=player.uid,
        player_name=player.name,
        from_team=from_team,
        to_team=new_team.name,
        from_team_id=from_team_record.id if from_team_record else None,
        to_team_id=new_team.id,
        operation="交易",
        operator=admin,
        notes=request.notes or "",
    )
    persist_with_team_stats(
        db,
        affected_team_ids={from_team_id, new_team.id},
        stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
    )

    log_detail = f"球员 {player.name}(UID:{player.uid}) 从 {from_team} 转移到 {new_team.name}"
    write_to_log("交易", log_detail, admin)
    return {"success": True, "message": f"{player.name} 已从 {from_team} 转移到 {new_team.name}"}


def fish_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    existing = get_player_by_uid(db, request.uid)
    if existing:
        raise HTTPException(status_code=400, detail="该UID已存在")

    team = get_team_by_name(db, request.team_name)
    if not team:
        raise HTTPException(status_code=404, detail="目标球队不存在")

    new_player = Player(
        uid=request.uid,
        name=request.name,
        age=request.age,
        initial_ca=request.ca,
        ca=request.ca,
        pa=request.pa,
        position=request.position,
        nationality=request.nationality,
        team_id=team.id,
        team_name=team.name,
        wage=0,
        slot_type="",
    )
    refresh_player_financials(new_player, db)
    db.add(new_player)

    create_transfer_log(
        db,
        player_uid=request.uid,
        player_name=request.name,
        from_team="球员库",
        to_team=team.name,
        to_team_id=team.id,
        operation="海捞",
        operator=admin,
        notes=request.notes or "",
    )
    persist_with_team_stats(
        db,
        affected_team_ids={team.id},
        stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
    )

    log_detail = f"球员 {request.name}(UID:{request.uid}) 从球员库海捞至 {team.name}"
    write_to_log("海捞", log_detail, admin)
    return {"success": True, "message": f"{request.name} 已成功加入 {team.name}"}


def release_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    player = get_player_by_uid(db, request.player_uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")

    sea_team = get_sea_team(db)
    if not sea_team:
        raise HTTPException(status_code=404, detail="大海球队不存在")

    from_team = player.team_name
    from_team_id = player.team_id
    from_team_record = get_team_by_name(db, from_team) if from_team else None
    assign_player_team(player, sea_team)

    create_transfer_log(
        db,
        player_uid=player.uid,
        player_name=player.name,
        from_team=from_team,
        to_team=sea_team.name,
        from_team_id=from_team_record.id if from_team_record else None,
        to_team_id=sea_team.id,
        operation="解约",
        operator=admin,
        notes=request.notes or "",
    )
    persist_with_team_stats(
        db,
        affected_team_ids={from_team_id, sea_team.id},
        stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
    )

    log_detail = f"球员 {player.name}(UID:{player.uid}) 从 {from_team} 解约进入 {sea_team.name}"
    write_to_log("解约", log_detail, admin)
    return {"success": True, "message": f"{player.name} 已解约进入 {sea_team.name}"}


def batch_transfer(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    results = []
    success_count = 0
    affected_team_ids: set[int | None] = set()

    for item in request.items:
        player = get_player_by_uid(db, item.uid)
        if not player:
            results.append({"uid": item.uid, "success": False, "message": "球员不存在"})
            continue

        new_team = get_team_by_name(db, item.to_team)
        if not new_team:
            results.append({"uid": item.uid, "success": False, "message": "目标球队不存在"})
            continue

        from_team = player.team_name
        affected_team_ids.add(player.team_id)
        from_team_record = get_team_by_name(db, from_team) if from_team else None
        assign_player_team(player, new_team)
        affected_team_ids.add(new_team.id)
        create_transfer_log(
            db,
            player_uid=player.uid,
            player_name=player.name,
            from_team=from_team,
            to_team=new_team.name,
            from_team_id=from_team_record.id if from_team_record else None,
            to_team_id=new_team.id,
            operation="批量交易",
            operator=admin,
            notes=item.notes or "",
        )
        results.append({"uid": item.uid, "success": True, "message": f"{player.name}: {from_team}→{new_team.name}"})
        success_count += 1

    if success_count:
        persist_with_team_stats(
            db,
            affected_team_ids=affected_team_ids,
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
        )

    log_detail = f"批量交易 {success_count}/{len(request.items)} 条记录成功"
    write_to_log("批量交易", log_detail, admin)
    return {"success": True, "results": results, "success_count": success_count}


def batch_release(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    admin = require_admin(admin)
    results = []
    success_count = 0
    affected_team_ids: set[int | None] = set()

    sea_team = get_sea_team(db)
    if not sea_team:
        raise HTTPException(status_code=404, detail="大海球队不存在")

    for item in request.items:
        player = get_player_by_uid(db, item.uid)
        if not player:
            results.append({"uid": item.uid, "success": False, "message": "球员不存在"})
            continue

        from_team = player.team_name
        affected_team_ids.add(player.team_id)
        from_team_record = get_team_by_name(db, from_team) if from_team else None
        assign_player_team(player, sea_team)
        affected_team_ids.add(sea_team.id)
        create_transfer_log(
            db,
            player_uid=player.uid,
            player_name=player.name,
            from_team=from_team,
            to_team=sea_team.name,
            from_team_id=from_team_record.id if from_team_record else None,
            to_team_id=sea_team.id,
            operation="批量解约",
            operator=admin,
            notes=item.notes or "",
        )
        results.append({"uid": item.uid, "success": True, "message": f"{player.name}: {from_team}→{sea_team.name}"})
        success_count += 1

    if success_count:
        persist_with_team_stats(
            db,
            affected_team_ids=affected_team_ids,
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
        )

    log_detail = f"批量解约 {success_count}/{len(request.items)} 条记录成功"
    write_to_log("批量解约", log_detail, admin)
    return {"success": True, "results": results, "success_count": success_count}


def undo_operation(db: Session, admin: str | None, log_id: int, write_to_log: LogWriter):
    admin = require_admin(admin)
    log = get_transfer_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="操作记录不存在")

    player = get_player_by_uid(db, log.player_uid)
    undo_details = []

    if log.operation in ["交易", "批量交易", "解约", "批量解约"]:
        stat_scopes = set(PERSISTED_TEAM_STAT_SCOPES)
        if not player:
            raise HTTPException(status_code=404, detail="球员不存在")
        current_team = player.team_name
        current_team_id = player.team_id
        from_team = get_team_by_id(db, log.from_team_id) if log.from_team_id else None
        if from_team:
            assign_player_team(player, from_team)
            target_team_name = from_team.name
            target_team_id = from_team.id
        else:
            assign_player_team_by_name(db, player, log.from_team)
            target_team_name = log.from_team
            target_team_id = player.team_id
        undo_details.append(f"球队: {current_team} → {target_team_name}")
    elif log.operation == "海捞":
        stat_scopes = set(PERSISTED_TEAM_STAT_SCOPES)
        current_team_id = player.team_id if player else None
        target_team_id = None
        if player:
            db.delete(player)
        undo_details.append("球员已从数据库删除")
    else:
        from services.roster_service import undo_roster_operation

        handled, detail, stat_scopes = undo_roster_operation(db, log, player)
        if not handled:
            raise HTTPException(status_code=400, detail="不支持撤销该类型操作")
        current_team_id = player.team_id if player else None
        target_team_id = player.team_id if player else None
        undo_details.append(detail)

    db.delete(log)
    persist_with_team_stats(
        db,
        affected_team_ids={current_team_id, target_team_id},
        stat_scopes=stat_scopes,
    )

    log_detail = f"撤销操作 ID:{log_id} - {log.operation} - 球员:{log.player_name} - {', '.join(undo_details)}"
    write_to_log("撤销", log_detail, admin)
    return {"success": True, "message": f"已撤销操作: {log.operation} - {log.player_name}"}
