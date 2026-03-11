from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from schemas_read import (
    AttributeSearchResponse,
    HealthResponse,
    LeagueInfoResponse,
    PlayerAttributeDetailResponse,
    PlayerResponse,
    TeamResponse,
    WageDetailResponse,
)
from services import export_service, read_service


def build_public_router(get_db):
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        return HealthResponse(status="healthy", timestamp=datetime.now().isoformat())

    @router.get("/api/league/info", response_model=list[LeagueInfoResponse])
    def get_league_info(db: Session = Depends(get_db)):
        return read_service.get_league_info(db)

    @router.get("/api/teams", response_model=list[TeamResponse])
    def get_teams(db: Session = Depends(get_db)):
        return read_service.get_teams(db)

    @router.get("/api/players", response_model=list[PlayerResponse])
    def get_all_players(db: Session = Depends(get_db)):
        return read_service.get_all_players(db)

    @router.get("/api/players/team/{team_name:path}", response_model=list[PlayerResponse])
    def get_players_by_team(team_name: str, db: Session = Depends(get_db)):
        return read_service.get_players_by_team(db, team_name)

    @router.get("/api/players/search/{player_name}", response_model=list[PlayerResponse])
    def search_player(player_name: str, db: Session = Depends(get_db)):
        return read_service.search_player(db, player_name)

    @router.get("/api/attributes/search/{player_name}", response_model=list[AttributeSearchResponse])
    def search_player_attributes(player_name: str, db: Session = Depends(get_db)):
        return read_service.search_player_attributes(db, player_name)

    @router.get("/api/attributes/{uid}", response_model=PlayerAttributeDetailResponse | None)
    def get_player_attribute_detail(uid: int, db: Session = Depends(get_db)):
        return read_service.get_player_attribute_detail(db, uid)

    @router.get("/api/export/excel")
    def export_excel(db: Session = Depends(get_db)):
        output, filename = export_service.build_export_excel(db)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/api/player/wage-detail/{uid}", response_model=WageDetailResponse)
    def get_player_wage_detail(uid: int, db: Session = Depends(get_db)):
        return read_service.get_player_wage_detail(db, uid)

    return router
