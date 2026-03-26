import os

from app_bootstrap import LOG_FILE, load_bootstrap_admin_accounts_from_env, shutdown_app_state, write_to_log
from app_factory import app, get_db, health_check, verify_admin
from app_security import (
    clear_session_cookie,
    get_session_cookie_secure_mode,
    request_uses_https,
    set_session_cookie,
    should_use_secure_session_cookie,
)
from database import engine
from models import Player
from services import league_service

LOCAL_DEV_HOST = os.environ.get("LOCAL_HOST", "127.0.0.1")
LOCAL_DEV_PORT = int(os.environ.get("LOCAL_PORT", "8001"))


def calculate_player_wage_payload(initial_ca: int, current_ca: int, pa: int, age: int, position: str, db):
    return league_service.calculate_player_wage_payload(
        initial_ca=initial_ca,
        current_ca=current_ca,
        pa=pa,
        age=age,
        position=position,
        db=db,
    )


def refresh_player_financials(player: Player, db):
    return league_service.refresh_player_financials(player, db)


def recalculate_team_stats(db, commit: bool = True, affected_team_ids=None, stat_scopes=None, refresh_mode=None):
    league_service.recalculate_team_stats(
        db,
        commit=commit,
        affected_team_ids=affected_team_ids,
        stat_scopes=stat_scopes,
        refresh_mode=refresh_mode,
    )


def calculate_team_final_wage(team, players):
    return league_service.calculate_team_final_wage(team, players)


def run_local_server():
    import uvicorn

    os.environ.setdefault("ALLOW_MANUAL_RUNTIME_FALLBACK", "1")
    uvicorn.run("main1:app", host=LOCAL_DEV_HOST, port=LOCAL_DEV_PORT, reload=False)


if __name__ == "__main__":
    run_local_server()
