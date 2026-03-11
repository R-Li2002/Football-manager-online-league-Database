import io
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from models import Team
from repositories.player_repository import list_players_excluding_team
from repositories.team_repository import list_visible_teams
from schemas_read import PlayerExportRow, TeamExportRow
from team_links import SEA_TEAM_NAME
from services.league_service import REALTIME_TEAM_STAT_SCOPES, collect_team_stat_overlays

LEVEL_ORDER = {"超级": 1, "甲级": 2, "乙级": 3}
VISIBLE_LEVEL = "隐藏"


def _get_export_teams(db: Session) -> list[Team]:
    teams = list_visible_teams(db, VISIBLE_LEVEL)
    return sorted(teams, key=lambda team: (LEVEL_ORDER.get(team.level, 99), team.name))


def _get_export_players(db: Session):
    return list_players_excluding_team(db, SEA_TEAM_NAME)


def build_export_excel(db: Session):
    output = io.BytesIO()
    export_teams = _get_export_teams(db)
    realtime_overlays = collect_team_stat_overlays(db, export_teams, stat_scopes=REALTIME_TEAM_STAT_SCOPES)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        team_rows = [
            TeamExportRow(
                level=team.level,
                team_name=team.name,
                manager=team.manager or "",
                team_size=team.team_size,
                gk_count=team.gk_count,
                extra_wage=team.extra_wage or 0,
                after_tax=team.after_tax or 0,
                final_wage=team.final_wage,
                count_8m=team.count_8m,
                count_7m=team.count_7m,
                count_fake=team.count_fake,
                total_value=realtime_overlays.get(team.id, {}).get("total_value", team.total_value),
                avg_value=realtime_overlays.get(team.id, {}).get("avg_value", team.avg_value),
                avg_ca=realtime_overlays.get(team.id, {}).get("avg_ca", team.avg_ca),
                avg_pa=realtime_overlays.get(team.id, {}).get("avg_pa", team.avg_pa),
                total_growth=realtime_overlays.get(team.id, {}).get("total_growth", team.total_growth),
                notes=team.notes or "",
            ).model_dump(by_alias=True)
            for team in export_teams
        ]
        pd.DataFrame(team_rows).to_excel(writer, sheet_name="信息总览", index=False, startrow=1)

        player_rows = [
            PlayerExportRow(
                uid=player.uid,
                name=player.name,
                age=player.age,
                initial_ca=player.initial_ca,
                ca=player.ca,
                pa=player.pa,
                position=player.position,
                nationality=player.nationality,
                team_name=player.team_name,
                wage=player.wage,
                slot_type=player.slot_type or "",
            ).model_dump(by_alias=True)
            for player in _get_export_players(db)
        ]
        pd.DataFrame(player_rows).to_excel(writer, sheet_name="联赛名单", index=False)

    output.seek(0)
    filename = f"heigo_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return output, filename
