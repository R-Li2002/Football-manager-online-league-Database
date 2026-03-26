from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Player, TransferLog
from repositories.player_repository import get_player_by_uid, get_team_players
from repositories.team_repository import get_other_team_by_name, get_team_by_name
from repositories.transfer_log_repository import update_player_uid_references
from services.admin_action_runner import AdminMutationResult, run_admin_mutation
from services.admin_common import LogWriter
from services.league_service import PERSISTED_TEAM_STAT_SCOPES, TEAM_STAT_SCOPE_WAGE, refresh_player_financials

PLAYER_NOT_FOUND = "\u7403\u5458\u4e0d\u5b58\u5728"
TEAM_NOT_FOUND = "\u7403\u961f\u4e0d\u5b58\u5728"
TEAM_NAME_EXISTS = "\u7403\u961f\u540d\u5df2\u5b58\u5728"
CONSUME_LABEL = "\u6d88\u8d39"
REJUVENATE_LABEL = "\u8fd4\u8001"
BATCH_CONSUME_LABEL = "\u6279\u91cf\u6d88\u8d39"
TEAM_UPDATE_LABEL = "\u7403\u961f\u4fee\u6539"
PLAYER_UPDATE_LABEL = "\u7403\u5458\u4fee\u6539"
UID_UPDATE_LABEL = "UID\u4fee\u6539"


def consume_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        player = get_player_by_uid(db, request.player_uid)
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)

        old_ca, old_pa = player.ca, player.pa
        player.ca = max(1, player.ca + request.ca_change)
        player.pa = max(1, player.pa + request.pa_change)
        refresh_player_financials(player, db)
        return AdminMutationResult(
            message=f"{player.name} CA {old_ca}->{player.ca}, PA {old_pa}->{player.pa}",
            log_action=CONSUME_LABEL,
            log_detail=f"player {player.uid} consume CA {old_ca}->{player.ca}, PA {old_pa}->{player.pa}",
            affected_team_ids={player.team_id},
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=[
                {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "from_team": player.team_name,
                    "to_team": player.team_name,
                    "from_team_id": player.team_id,
                    "to_team_id": player.team_id,
                    "operation": CONSUME_LABEL,
                    "notes": request.notes or "",
                    "ca_change": request.ca_change,
                    "pa_change": request.pa_change,
                }
            ],
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def rejuvenate_player(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        player = get_player_by_uid(db, request.player_uid)
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)

        old_age = player.age
        player.age = max(15, player.age - request.age_change)
        refresh_player_financials(player, db)
        return AdminMutationResult(
            message=f"{player.name} age {old_age}->{player.age}",
            log_action=REJUVENATE_LABEL,
            log_detail=f"player {player.uid} rejuvenate age {old_age}->{player.age}",
            affected_team_ids={player.team_id},
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=[
                {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "from_team": player.team_name,
                    "to_team": player.team_name,
                    "from_team_id": player.team_id,
                    "to_team_id": player.team_id,
                    "operation": REJUVENATE_LABEL,
                    "notes": request.notes or "",
                    "age_change": request.age_change,
                }
            ],
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def batch_consume(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
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

            old_ca, old_pa = player.ca, player.pa
            player.ca = max(1, player.ca + item.ca_change)
            player.pa = max(1, player.pa + item.pa_change)
            refresh_player_financials(player, db)
            affected_team_ids.add(player.team_id)
            transfer_logs.append(
                {
                    "player_uid": player.uid,
                    "player_name": player.name,
                    "from_team": player.team_name,
                    "to_team": player.team_name,
                    "from_team_id": player.team_id,
                    "to_team_id": player.team_id,
                    "operation": BATCH_CONSUME_LABEL,
                    "notes": item.notes or "",
                    "ca_change": item.ca_change,
                    "pa_change": item.pa_change,
                }
            )
            results.append({"uid": item.uid, "success": True, "message": f"{player.name}: CA {old_ca}->{player.ca}, PA {old_pa}->{player.pa}"})
            success_count += 1

        return AdminMutationResult(
            message=f"batch consume finished {success_count}/{len(request.items)}",
            log_action=BATCH_CONSUME_LABEL,
            log_detail=f"batch consume {success_count}/{len(request.items)}",
            affected_team_ids=affected_team_ids,
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
            transfer_logs=transfer_logs,
            response_payload={"results": results, "success_count": success_count},
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def update_team_info(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        team = get_team_by_name(db, request.team_name)
        if not team:
            raise HTTPException(status_code=404, detail=TEAM_NOT_FOUND)

        old_manager = team.manager
        old_name = team.name
        old_notes = team.notes
        old_level = team.level

        if request.manager is not None:
            team.manager = request.manager
        if request.name is not None:
            existing = get_other_team_by_name(db, request.name, team.id)
            if existing:
                raise HTTPException(status_code=400, detail=TEAM_NAME_EXISTS)
            players = get_team_players(db, team)
            for player in players:
                player.team_id = team.id
                player.team_name = request.name
            team.name = request.name
        if request.notes is not None:
            team.notes = request.notes
        if request.level is not None:
            team.level = request.level

        changes = []
        if request.manager is not None and request.manager != old_manager:
            changes.append(f"manager {old_manager}->{request.manager}")
        if request.name is not None and request.name != old_name:
            changes.append(f"name {old_name}->{request.name}")
        if request.notes is not None and request.notes != old_notes:
            changes.append("notes updated")
        if request.level is not None and request.level != old_level:
            changes.append(f"level {old_level}->{request.level}")
        if not changes:
            changes.append("no field changes")

        affected_scopes = set()
        if request.level is not None and request.level != old_level:
            affected_scopes.add(TEAM_STAT_SCOPE_WAGE)
        if request.notes is not None and request.notes != old_notes:
            affected_scopes.add(TEAM_STAT_SCOPE_WAGE)

        return AdminMutationResult(
            message=f"team updated: {', '.join(changes)}",
            log_action=TEAM_UPDATE_LABEL,
            log_detail=f"team {old_name} updated: {', '.join(changes)}",
            affected_team_ids={team.id} if affected_scopes else set(),
            stat_scopes=affected_scopes if affected_scopes else None,
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def update_player_info(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        player = get_player_by_uid(db, request.uid)
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)

        old_name = player.name
        old_position = player.position
        old_nationality = player.nationality
        old_age = player.age

        changes = []
        if request.name is not None and request.name != player.name:
            player.name = request.name
            changes.append(f"name {old_name}->{request.name}")
        if request.position is not None and request.position != player.position:
            player.position = request.position
            changes.append(f"position {old_position}->{request.position}")
        if request.nationality is not None and request.nationality != player.nationality:
            player.nationality = request.nationality
            changes.append(f"nationality {old_nationality}->{request.nationality}")
        if request.age is not None and request.age != player.age:
            player.age = request.age
            changes.append(f"age {old_age}->{request.age}")

        should_refresh_financials = request.position is not None or request.age is not None
        if should_refresh_financials:
            refresh_player_financials(player, db)

        if not changes:
            changes.append("no field changes")

        return AdminMutationResult(
            message=f"player updated: {', '.join(changes)}",
            log_action=PLAYER_UPDATE_LABEL,
            log_detail=f"player {request.uid} updated: {', '.join(changes)}",
            affected_team_ids={player.team_id} if should_refresh_financials else set(),
            stat_scopes=PERSISTED_TEAM_STAT_SCOPES if should_refresh_financials else None,
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def update_player_uid(db: Session, admin: str | None, request: Any, write_to_log: LogWriter):
    def mutate(_operator: str) -> AdminMutationResult:
        player = get_player_by_uid(db, request.old_uid)
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)

        existing_player = get_player_by_uid(db, request.new_uid)
        if existing_player:
            raise HTTPException(status_code=400, detail=f"UID {request.new_uid} already in use")

        old_uid = player.uid
        player.uid = request.new_uid
        update_player_uid_references(db, old_uid, request.new_uid)
        return AdminMutationResult(
            message=f"player UID updated {old_uid}->{request.new_uid}",
            log_action=UID_UPDATE_LABEL,
            log_detail=f"player {player.name} UID updated {old_uid}->{request.new_uid}",
        )

    return run_admin_mutation(db, admin, write_to_log, mutator=mutate)


def undo_roster_operation(db: Session, log: TransferLog, player: Player | None) -> tuple[bool, str, set[str]]:
    if log.operation in [CONSUME_LABEL, BATCH_CONSUME_LABEL]:
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)
        if log.ca_change:
            player.ca = max(1, player.ca - log.ca_change)
        if log.pa_change:
            player.pa = max(1, player.pa - log.pa_change)
        refresh_player_financials(player, db)
        return True, f"CA/PA rolled back to {player.ca}/{player.pa}", set(PERSISTED_TEAM_STAT_SCOPES)

    if log.operation == REJUVENATE_LABEL:
        if not player:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)
        if log.age_change:
            player.age = player.age + log.age_change
        refresh_player_financials(player, db)
        return True, f"age rolled back to {player.age}", set(PERSISTED_TEAM_STAT_SCOPES)

    return False, "", set()
