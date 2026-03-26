from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Player
from repositories.player_repository import get_player_by_uid
from repositories.team_repository import get_team_by_id, get_team_by_name
from repositories.transfer_log_repository import get_transfer_log_by_id
from services.admin_action_runner import AdminMutationResult, run_admin_mutation
from services.admin_common import LogWriter
from services.league_service import PERSISTED_TEAM_STAT_SCOPES, refresh_player_financials
from services.roster_service import undo_roster_operation
from team_links import assign_player_team, assign_player_team_by_name, get_sea_team

PLAYER_NOT_FOUND = "\u7403\u5458\u4e0d\u5b58\u5728"
TARGET_TEAM_NOT_FOUND = "\u76ee\u6807\u7403\u961f\u4e0d\u5b58\u5728"
SEA_TEAM_NOT_FOUND = "\u5927\u6d77\u7403\u961f\u4e0d\u5b58\u5728"
UID_EXISTS = "UID already exists"
LOG_NOT_FOUND = "\u64cd\u4f5c\u8bb0\u5f55\u4e0d\u5b58\u5728"
UNSUPPORTED_UNDO = "\u4e0d\u652f\u6301\u64a4\u9500\u8be5\u7c7b\u578b\u64cd\u4f5c"
PLAYER_POOL = "\u7403\u5458\u5e93"
TRADE_LABEL = "\u4ea4\u6613"
FISH_LABEL = "\u6d77\u635e"
RELEASE_LABEL = "\u89e3\u7ea6"
BATCH_TRADE_LABEL = "\u6279\u91cf\u4ea4\u6613"
BATCH_RELEASE_LABEL = "\u6279\u91cf\u89e3\u7ea6"
UNDO_LABEL = "\u64a4\u9500"


def transfer_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        player = get_player_by_uid(db, request.player_uid)
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)

        new_team = get_team_by_name(db, request.to_team)
        if not new_team:
            raise HTTPException(status_code=404, detail=TARGET_TEAM_NOT_FOUND)

        from_team = player.team_name
        from_team_id = player.team_id
        assign_player_team(player, new_team)
        return AdminMutationResult(
            message=f"{player.name} moved from {from_team} to {new_team.name}",
            log_action=TRADE_LABEL,
            log_detail=f"player {player.uid} moved from {from_team} to {new_team.name}",
            affected_team_ids={from_team_id, new_team.id},
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=[
                {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "from_team": from_team,
                    "to_team": new_team.name,
                    "from_team_id": from_team_id,
                    "to_team_id": new_team.id,
                    "operation": TRADE_LABEL,
                    "notes": request.notes or "",
                }
            ],
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def fish_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        existing = get_player_by_uid(db, request.uid)
        if existing:
            raise HTTPException(status_code=400, detail=UID_EXISTS)

        team = get_team_by_name(db, request.team_name)
        if not team:
            raise HTTPException(status_code=404, detail=TARGET_TEAM_NOT_FOUND)

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
        return AdminMutationResult(
            message=f"{request.name} added to {team.name}",
            log_action=FISH_LABEL,
            log_detail=f"player {request.uid} fished into {team.name}",
            affected_team_ids={team.id},
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=[
                {
                    "player_uid": request.uid,
                    "player_name": request.name,
                    "from_team": PLAYER_POOL,
                    "to_team": team.name,
                    "to_team_id": team.id,
                    "operation": FISH_LABEL,
                    "notes": request.notes or "",
                }
            ],
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def release_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        player = get_player_by_uid(db, request.player_uid)
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)

        sea_team = get_sea_team(db)
        if not sea_team:
            raise HTTPException(status_code=404, detail=SEA_TEAM_NOT_FOUND)

        from_team = player.team_name
        from_team_id = player.team_id
        assign_player_team(player, sea_team)
        return AdminMutationResult(
            message=f"{player.name} released to {sea_team.name}",
            log_action=RELEASE_LABEL,
            log_detail=f"player {player.uid} released from {from_team} to {sea_team.name}",
            affected_team_ids={from_team_id, sea_team.id},
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=[
                {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "from_team": from_team,
                    "to_team": sea_team.name,
                    "from_team_id": from_team_id,
                    "to_team_id": sea_team.id,
                    "operation": RELEASE_LABEL,
                    "notes": request.notes or "",
                }
            ],
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def batch_transfer(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        results = []
        success_count = 0
        affected_team_ids: set[int | None] = set()
        transfer_logs = []

        for item in request.items:
            player = get_player_by_uid(db, item.uid)
            if not player:
                results.append({"uid": item.uid, "success": False, "message": PLAYER_NOT_FOUND})
                continue

            new_team = get_team_by_name(db, item.to_team)
            if not new_team:
                results.append({"uid": item.uid, "success": False, "message": TARGET_TEAM_NOT_FOUND})
                continue

            from_team = player.team_name
            from_team_id = player.team_id
            assign_player_team(player, new_team)
            affected_team_ids.update({from_team_id, new_team.id})
            transfer_logs.append(
                {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "from_team": from_team,
                    "to_team": new_team.name,
                    "from_team_id": from_team_id,
                    "to_team_id": new_team.id,
                    "operation": BATCH_TRADE_LABEL,
                    "notes": item.notes or "",
                }
            )
            results.append({"uid": item.uid, "success": True, "message": f"{player.name}: {from_team}->{new_team.name}"})
            success_count += 1

        return AdminMutationResult(
            message=f"batch transfer finished {success_count}/{len(request.items)}",
            log_action=BATCH_TRADE_LABEL,
            log_detail=f"batch transfer {success_count}/{len(request.items)}",
            affected_team_ids=affected_team_ids,
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=transfer_logs,
            response_payload={"results": results, "success_count": success_count},
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def batch_release(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        results = []
        success_count = 0
        affected_team_ids: set[int | None] = set()
        transfer_logs = []

        sea_team = get_sea_team(db)
        if not sea_team:
            raise HTTPException(status_code=404, detail=SEA_TEAM_NOT_FOUND)

        for item in request.items:
            player = get_player_by_uid(db, item.uid)
            if not player:
                results.append({"uid": item.uid, "success": False, "message": PLAYER_NOT_FOUND})
                continue

            from_team = player.team_name
            from_team_id = player.team_id
            assign_player_team(player, sea_team)
            affected_team_ids.update({from_team_id, sea_team.id})
            transfer_logs.append(
                {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "from_team": from_team,
                    "to_team": sea_team.name,
                    "from_team_id": from_team_id,
                    "to_team_id": sea_team.id,
                    "operation": BATCH_RELEASE_LABEL,
                    "notes": item.notes or "",
                }
            )
            results.append({"uid": item.uid, "success": True, "message": f"{player.name}: {from_team}->{sea_team.name}"})
            success_count += 1

        return AdminMutationResult(
            message=f"batch release finished {success_count}/{len(request.items)}",
            log_action=BATCH_RELEASE_LABEL,
            log_detail=f"batch release {success_count}/{len(request.items)}",
            affected_team_ids=affected_team_ids,
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=transfer_logs,
            response_payload={"results": results, "success_count": success_count},
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def undo_operation(db: Session, admin: str | None, log_id: int, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        log = get_transfer_log_by_id(db, log_id)
        if not log:
            raise HTTPException(status_code=404, detail=LOG_NOT_FOUND)

        player = get_player_by_uid(db, log.player_uid)
        undo_details = []
        current_team_id = player.team_id if player else None
        target_team_id = player.team_id if player else None

        if log.operation in [TRADE_LABEL, BATCH_TRADE_LABEL, RELEASE_LABEL, BATCH_RELEASE_LABEL]:
            stat_scopes = set(PERSISTED_TEAM_STAT_SCOPES)
            if not player:
                raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)
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
            undo_details.append(f"team {current_team}->{target_team_name}")
        elif log.operation == FISH_LABEL:
            stat_scopes = set(PERSISTED_TEAM_STAT_SCOPES)
            current_team_id = player.team_id if player else None
            target_team_id = None
            if player:
                db.delete(player)
            undo_details.append("player removed")
        else:
            handled, detail, stat_scopes = undo_roster_operation(db, log, player)
            if not handled:
                raise HTTPException(status_code=400, detail=UNSUPPORTED_UNDO)
            current_team_id = player.team_id if player else None
            target_team_id = player.team_id if player else None
            undo_details.append(detail)

        db.delete(log)
        return AdminMutationResult(
            message=f"undid {log.operation} for {log.player_name}",
            log_action=UNDO_LABEL,
            log_detail=f"undo log {log_id}: {log.operation} {'; '.join(undo_details)}",
            affected_team_ids={current_team_id, target_team_id},
            stat_scopes=stat_scopes,
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)
