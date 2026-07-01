import os
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from schemas_read import (
    AdvancedAttributeSearchResponse,
    AttributeSearchResponse,
    AttributeVersionsResponse,
    CoachDetailResponse,
    CoachesResponse,
    CoachReactionActionResponse,
    DataFeedbackSubmitResponse,
    CupBracketResponse,
    LeagueInfoResponse,
    ScheduleResponse,
    PlayerReactionActionResponse,
    PlayerReactionLeaderboardResponse,
    PlayerAttributeDetailResponse,
    PlayerRankingsResponse,
    PlayerResponse,
    ProjectUpdateEntryResponse,
    SiteNoteResponse,
    StandingsResponse,
    SuspensionsResponse,
    TeamResponse,
    WageDetailResponse,
)
from schemas_write import AdvancedAttributeSearchRequest, DataFeedbackRequest
from services import coach_service, cup_service, data_feedback_service, export_service, player_ranking_service, project_update_service, read_service, reaction_service, site_note_service, suspension_service

REACTION_VISITOR_COOKIE_NAME = "heigo_reaction_visitor"
REACTION_VISITOR_COOKIE_MAX_AGE_SECONDS = 31536000
REACTION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}


def build_public_router(get_db):
    router = APIRouter()

    def ensure_reaction_visitor_token(response: Response, visitor_token: str | None) -> str:
        if visitor_token:
            return visitor_token

        generated_token = uuid4().hex
        response.set_cookie(
            key=REACTION_VISITOR_COOKIE_NAME,
            value=generated_token,
            httponly=False,
            samesite="lax",
            secure=REACTION_COOKIE_SECURE,
            max_age=REACTION_VISITOR_COOKIE_MAX_AGE_SECONDS,
            path="/",
        )
        return generated_token

    @router.get("/api/league/info", response_model=list[LeagueInfoResponse])
    def get_league_info(db: Session = Depends(get_db)):
        return read_service.get_league_info(db)

    @router.get("/api/teams", response_model=list[TeamResponse])
    def get_teams(db: Session = Depends(get_db)):
        return read_service.get_teams(db)

    @router.get("/api/coaches", response_model=CoachesResponse)
    def get_coaches(
        visitor_token: str | None = Cookie(None, alias=REACTION_VISITOR_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.get_coaches(db, visitor_token=visitor_token)

    @router.get("/api/coaches/{coach_uid}", response_model=CoachDetailResponse)
    def get_coach_detail(
        coach_uid: str,
        visitor_token: str | None = Cookie(None, alias=REACTION_VISITOR_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.get_coach_detail(db, coach_uid, visitor_token=visitor_token)

    @router.post("/api/coaches/{coach_uid}/reactions/{reaction_type}", response_model=CoachReactionActionResponse)
    def react_to_coach(
        coach_uid: str,
        reaction_type: str,
        response: Response,
        visitor_token: str | None = Cookie(None, alias=REACTION_VISITOR_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        stable_visitor_token = ensure_reaction_visitor_token(response, visitor_token)
        return coach_service.record_coach_reaction(db, coach_uid, stable_visitor_token, reaction_type)

    @router.get("/api/players", response_model=list[PlayerResponse])
    def get_all_players(db: Session = Depends(get_db)):
        return read_service.get_all_players(db)

    @router.get("/api/players/team/{team_name:path}", response_model=list[PlayerResponse])
    def get_players_by_team(team_name: str, db: Session = Depends(get_db)):
        return read_service.get_players_by_team(db, team_name)

    @router.get("/api/players/search/{player_name}", response_model=list[PlayerResponse])
    def search_player(player_name: str, db: Session = Depends(get_db)):
        return read_service.search_player(db, player_name)

    @router.get("/api/matches", response_model=ScheduleResponse)
    def get_matches(
        level: str | None = None,
        round_no: int | None = None,
        db: Session = Depends(get_db),
    ):
        return read_service.get_schedule(db, level=level, round_no=round_no)

    @router.get("/api/standings", response_model=StandingsResponse)
    def get_standings(db: Session = Depends(get_db)):
        return read_service.get_standings(db)

    @router.get("/api/player-rankings", response_model=PlayerRankingsResponse)
    def get_player_rankings(db: Session = Depends(get_db)):
        return player_ranking_service.get_player_rankings(db)

    @router.get("/api/suspensions", response_model=SuspensionsResponse)
    def get_suspensions(db: Session = Depends(get_db)):
        return suspension_service.get_suspensions(db)

    @router.get("/api/site-notes", response_model=list[SiteNoteResponse])
    def get_site_notes(db: Session = Depends(get_db)):
        return site_note_service.list_site_notes(db)

    @router.get("/api/cups/{competition}/bracket", response_model=CupBracketResponse)
    def get_cup_bracket(competition: str, db: Session = Depends(get_db)):
        return cup_service.get_bracket(db, competition)

    @router.get("/api/attributes/search/{player_name}", response_model=list[AttributeSearchResponse])
    def search_player_attributes(
        player_name: str,
        version: str | None = None,
        db: Session = Depends(get_db),
    ):
        return read_service.search_player_attributes(db, player_name, data_version=version)

    @router.post("/api/attributes/advanced-search", response_model=AdvancedAttributeSearchResponse)
    def search_player_attributes_advanced(
        request: AdvancedAttributeSearchRequest,
        db: Session = Depends(get_db),
    ):
        return read_service.search_player_attributes_advanced_service(db, request)

    @router.get("/api/attributes/versions", response_model=AttributeVersionsResponse)
    def get_attribute_versions(db: Session = Depends(get_db)):
        return read_service.get_attribute_versions(db)

    @router.get("/api/attributes/{uid}", response_model=PlayerAttributeDetailResponse | None)
    def get_player_attribute_detail(
        uid: int,
        version: str | None = None,
        visitor_token: str | None = Cookie(None, alias=REACTION_VISITOR_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return read_service.get_player_attribute_detail(db, uid, data_version=version, visitor_token=visitor_token)

    @router.post("/api/attributes/{uid}/reactions/{reaction_type}", response_model=PlayerReactionActionResponse)
    def react_to_player(
        uid: int,
        reaction_type: str,
        response: Response,
        version: str | None = None,
        visitor_token: str | None = Cookie(None, alias=REACTION_VISITOR_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        stable_visitor_token = ensure_reaction_visitor_token(response, visitor_token)
        return reaction_service.record_player_reaction(
            db,
            player_uid=uid,
            visitor_token=stable_visitor_token,
            reaction_type=reaction_type,
            data_version=version,
        )

    @router.get("/api/reactions/leaderboard", response_model=PlayerReactionLeaderboardResponse)
    def get_player_reaction_leaderboard(
        metric: str = "flowers",
        limit: int = 20,
        team: str | None = None,
        version: str | None = None,
        db: Session = Depends(get_db),
    ):
        return read_service.get_player_reaction_leaderboard(
            db,
            metric=metric,
            limit=limit,
            team_name=team,
            data_version=version,
        )

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

    @router.get("/api/project-updates", response_model=list[ProjectUpdateEntryResponse])
    def get_project_updates(limit: int = 20):
        return project_update_service.list_project_updates(limit=limit)

    @router.post("/api/data-feedback", response_model=DataFeedbackSubmitResponse, status_code=201)
    def submit_data_feedback(request: DataFeedbackRequest, db: Session = Depends(get_db)):
        return data_feedback_service.submit_data_feedback(db, request)

    return router
