import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from schemas_read import (
    AdvancedAttributeSearchResponse,
    AttributeBatchLookupResponse,
    AttributeSearchResponse,
    AttributeVersionsResponse,
    CandidateListDetailResponse,
    CandidateListPlayersResponse,
    CandidateListSummaryResponse,
    CoachDetailResponse,
    CoachesResponse,
    CoachReactionActionResponse,
    DataFeedbackSubmitResponse,
    DailyReportResponse,
    DataStatusResponse,
    HomeDashboardResponse,
    HomePromotionResponse,
    HomeSummaryResponse,
    CupBracketResponse,
    CupGroupStageResponse,
    LeagueInfoResponse,
    ScheduleResponse,
    PlayerReactionActionResponse,
    PlayerReactionLeaderboardResponse,
    PlayerPowerCalibrationResponse,
    PlayerPowerRankingResponse,
    TeamPowerSummariesResponse,
    TeamCenterResponse,
    TeamCupOutlookResponse,
    PlayerAttributeDetailResponse,
    PlayerRankingsResponse,
    PlayerResponse,
    ProjectUpdateEntryResponse,
    RankingsResponse,
    SiteVisitStatsResponse,
    SiteNoteResponse,
    StandingsResponse,
    SuspensionsResponse,
    TeamResponse,
    TeamLineupResponse,
    WageDetailResponse,
)
from schemas_write import AdvancedAttributeSearchRequest, AttributeBatchLookupRequest, DataFeedbackRequest
from services import candidate_list_service, coach_service, cup_service, daily_report_image_service, daily_report_service, data_feedback_service, data_status_service, export_service, home_promotion_service, home_service, league_report_image_service, player_ranking_service, project_update_service, ranking_export_service, ranking_service, read_service, reaction_service, site_note_service, site_visit_service, suspension_service, team_center_service, team_lineup_service

REACTION_VISITOR_COOKIE_NAME = "heigo_reaction_visitor"
ADMIN_SESSION_COOKIE_NAME = "session_token"
COACH_SESSION_COOKIE_NAME = "coach_session_token"
REACTION_VISITOR_COOKIE_MAX_AGE_SECONDS = 31536000
REACTION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}
SHARE_CACHE_ROOT = Path(os.environ.get("HEIGO_SHARE_CACHE_ROOT", "data/share-cache").strip() or "data/share-cache")


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

    @router.get("/api/home/summary", response_model=HomeSummaryResponse)
    def get_home_summary(db: Session = Depends(get_db)):
        return home_service.get_home_summary(db)

    @router.get("/api/home/dashboard", response_model=HomeDashboardResponse)
    def get_home_dashboard(
        team_id: int | None = Query(None, ge=1),
        db: Session = Depends(get_db),
    ):
        return home_service.get_home_dashboard(db, team_id=team_id)

    @router.get("/api/daily-report", response_model=DailyReportResponse)
    def get_daily_report(
        report_date: str | None = Query(None),
        db: Session = Depends(get_db),
    ):
        return daily_report_service.get_public_report(db, report_date)

    @router.get("/api/daily-report/image", response_class=FileResponse)
    def get_daily_report_image(
        report_date: str | None = Query(None),
        fingerprint: str | None = Query(None, max_length=64),
        scope: str = Query("full", pattern="^(full|focus)$"),
        db: Session = Depends(get_db),
    ):
        report = daily_report_service.get_public_report(db, report_date)
        rendered = daily_report_image_service.render_daily_report_png(report, SHARE_CACHE_ROOT, scope=scope)
        report_label = "焦点头版" if scope == "focus" else "日报"
        return FileResponse(
            rendered.file_path,
            media_type="image/png",
            filename=f"HEIGO{report_label}-{report.report_date}.png",
            headers={
                "Cache-Control": "public, max-age=300",
                "ETag": rendered.etag,
                "X-Render-Cache": rendered.cache_status,
                "X-Report-Fingerprint": report.fingerprint,
            },
        )

    @router.get("/api/league-report/image", response_class=FileResponse)
    def get_league_report_image(
        kind: str = Query(..., pattern="^(standings|suspensions)$"),
        level: str = Query(..., pattern="^(超级|甲级|乙级)$"),
        fingerprint: str | None = Query(None, max_length=64),
        db: Session = Depends(get_db),
    ):
        payload = (
            suspension_service.get_suspensions(db, level=level)
            if kind == "suspensions"
            else read_service.get_standings(db, level=level)
        )
        rendered = league_report_image_service.render_league_report_png(kind, level, payload, SHARE_CACHE_ROOT)
        report_label = "伤停统计" if kind == "suspensions" else "积分榜"
        return FileResponse(
            rendered.file_path,
            media_type="image/png",
            filename=f"HEIGO-{level}-{report_label}.png",
            headers={
                "Cache-Control": "public, max-age=120",
                "ETag": rendered.etag,
                "X-Render-Cache": rendered.cache_status,
            },
        )

    @router.get("/api/statistics-report/image", response_class=FileResponse)
    def get_statistics_report_image(
        kind: str = Query(..., pattern="^(rankings|player_rankings)$"),
        level: str = Query("超级", pattern="^(超级|甲级|乙级)$"),
        metric: str = Query("goals", pattern="^(goals|assists|mvps)$"),
        fingerprint: str | None = Query(None, max_length=64),
        db: Session = Depends(get_db),
    ):
        payload = (
            player_ranking_service.get_player_rankings(db, level=level)
            if kind == "player_rankings"
            else ranking_service.get_rankings(db)
        )
        rendered = league_report_image_service.render_statistics_report_png(
            kind,
            payload,
            SHARE_CACHE_ROOT,
            level=level,
            metric=metric,
        )
        if kind == "player_rankings":
            metric_label = {"goals": "射手榜", "assists": "助攻榜", "mvps": "最佳球员榜"}[metric]
            file_name = f"HEIGO-{level}-{metric_label}.png"
        else:
            file_name = "HEIGO-排位积分榜.png"
        return FileResponse(
            rendered.file_path,
            media_type="image/png",
            filename=file_name,
            headers={
                "Cache-Control": "public, max-age=120",
                "ETag": rendered.etag,
                "X-Render-Cache": rendered.cache_status,
            },
        )

    @router.get("/api/data-status", response_model=DataStatusResponse)
    def get_data_status(db: Session = Depends(get_db)):
        return data_status_service.get_data_status(db)

    @router.get("/api/teams", response_model=list[TeamResponse])
    def get_teams(db: Session = Depends(get_db)):
        return read_service.get_teams(db)

    @router.get("/api/teams/{team_id}/lineup", response_model=TeamLineupResponse)
    def get_team_lineup(
        team_id: int,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return team_lineup_service.get_team_lineup(
            db,
            team_id,
            admin_session_token=admin_session_token,
            coach_session_token=coach_session_token,
        )

    @router.get("/api/teams/{team_id}/center", response_model=TeamCenterResponse)
    def get_team_center(
        team_id: int,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return team_center_service.get_team_center(
            db,
            team_id,
            admin_session_token=admin_session_token,
            coach_session_token=coach_session_token,
        )

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
    def get_standings(
        level: str | None = Query(None, pattern="^(超级|甲级|乙级)$"),
        db: Session = Depends(get_db),
    ):
        return read_service.get_standings(db, level=level)

    @router.get("/api/player-rankings", response_model=PlayerRankingsResponse)
    def get_player_rankings(
        level: str | None = Query(None, pattern="^(超级|甲级|乙级)$"),
        db: Session = Depends(get_db),
    ):
        return player_ranking_service.get_player_rankings(db, level=level)

    @router.get("/api/rankings", response_model=RankingsResponse)
    def get_rankings(db: Session = Depends(get_db)):
        return ranking_service.get_rankings(db)

    @router.get("/api/suspensions", response_model=SuspensionsResponse)
    def get_suspensions(
        level: str | None = Query(None, pattern="^(超级|甲级|乙级)$"),
        db: Session = Depends(get_db),
    ):
        return suspension_service.get_suspensions(db, level=level)

    @router.get("/api/site-notes", response_model=list[SiteNoteResponse])
    def get_site_notes(db: Session = Depends(get_db)):
        return site_note_service.list_site_notes(db)

    @router.get("/api/home-promotions", response_model=list[HomePromotionResponse])
    def get_home_promotions(db: Session = Depends(get_db)):
        return home_promotion_service.list_public_promotions(db)

    @router.post("/api/site-visits", response_model=SiteVisitStatsResponse)
    def record_site_visit(db: Session = Depends(get_db)):
        return site_visit_service.record_site_visit(db)

    @router.get("/api/cups/{competition}/bracket", response_model=CupBracketResponse)
    def get_cup_bracket(competition: str, db: Session = Depends(get_db)):
        return cup_service.get_bracket(db, competition)

    @router.get("/api/cups/{competition}/groups", response_model=CupGroupStageResponse)
    def get_cup_group_stage(competition: str, db: Session = Depends(get_db)):
        return cup_service.get_group_stage(db, competition)

    @router.get("/api/teams/{team_id}/cup-outlook", response_model=TeamCupOutlookResponse)
    def get_team_cup_outlook(team_id: int, db: Session = Depends(get_db)):
        return cup_service.get_team_cup_outlook(db, team_id)

    @router.get("/api/candidate-lists", response_model=list[CandidateListSummaryResponse])
    def get_candidate_lists(db: Session = Depends(get_db)):
        return candidate_list_service.list_public_candidate_lists(db)

    @router.get("/api/candidate-lists/{list_id}", response_model=CandidateListDetailResponse)
    def get_candidate_list(list_id: int, db: Session = Depends(get_db)):
        return candidate_list_service.get_candidate_list(db, list_id, public=True)

    @router.get("/api/candidate-lists/{list_id}/players", response_model=CandidateListPlayersResponse)
    def get_candidate_list_players(
        list_id: int,
        version: str | None = None,
        limit: int = 500,
        offset: int = 0,
        db: Session = Depends(get_db),
    ):
        return candidate_list_service.get_candidate_list_players(
            db,
            list_id,
            version=version,
            limit=limit,
            offset=offset,
            public=True,
        )

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

    @router.post("/api/attributes/batch-lookup", response_model=AttributeBatchLookupResponse)
    def batch_lookup_player_attributes(
        request: AttributeBatchLookupRequest,
        db: Session = Depends(get_db),
    ):
        return read_service.batch_lookup_player_attributes_service(db, request)

    @router.get("/api/attributes/versions", response_model=AttributeVersionsResponse)
    def get_attribute_versions(db: Session = Depends(get_db)):
        return read_service.get_attribute_versions(db)

    @router.get("/api/attributes/power-ranking", response_model=PlayerPowerRankingResponse)
    def get_player_power_ranking(
        shape: str = "all",
        limit: str = "50",
        team: str | None = None,
        version: str | None = None,
        db: Session = Depends(get_db),
    ):
        from services import player_power_ranking_service

        return player_power_ranking_service.get_player_power_ranking(
            db,
            shape=shape,
            limit=limit,
            team_name=team,
            data_version=version,
        )

    @router.get("/api/attributes/power-calibration", response_model=PlayerPowerCalibrationResponse)
    def get_player_power_calibration(
        version: str | None = None,
        db: Session = Depends(get_db),
    ):
        from services import player_power_ranking_service

        calibration = player_power_ranking_service.get_power_calibration(db, data_version=version)
        return PlayerPowerCalibrationResponse(
            data_version=calibration.data_version,
            player_count=calibration.player_count,
            median_score=calibration.median_score,
            mad=calibration.mad,
            robust_scale=calibration.robust_scale,
            sorted_scores=list(calibration.sorted_scores),
        )

    @router.get("/api/teams/power-summaries", response_model=TeamPowerSummariesResponse)
    def get_team_power_summaries(
        version: str | None = None,
        db: Session = Depends(get_db),
    ):
        from services import player_power_ranking_service

        return player_power_ranking_service.get_team_power_summaries(db, data_version=version)

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
        media_type = (
            "application/vnd.ms-excel.sheet.macroEnabled.12"
            if filename.lower().endswith(".xlsm")
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return StreamingResponse(
            output,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/api/export/suspensions.xlsx")
    def export_suspensions_excel(
        level: str = Query(...),
        db: Session = Depends(get_db),
    ):
        try:
            output, filename = export_service.build_suspensions_excel(db, level)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/api/export/standings.xlsx")
    def export_standings_excel(
        level: str = Query(...),
        db: Session = Depends(get_db),
    ):
        try:
            output, filename = export_service.build_standings_excel(db, level)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/api/export/rankings.xlsx")
    def export_rankings_excel(db: Session = Depends(get_db)):
        try:
            output, filename = ranking_export_service.build_ranking_excel(db)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
