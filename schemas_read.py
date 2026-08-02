from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class SiteVisitStatsResponse(BaseModel):
    total_count: int
    today_count: int
    visit_date: str


class HomeSummaryResponse(BaseModel):
    team_count: int = 0
    player_count: int = 0
    database_player_count: int = 0
    default_attribute_version: str = ""


class HomeDashboardMatchResponse(BaseModel):
    id: int
    level: str
    round_no: int
    home_team_id: Optional[int] = None
    home_team_name: str
    away_team_id: Optional[int] = None
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str
    match_date: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HomeDashboardLeaderResponse(BaseModel):
    level: str
    rank: int = 1
    team_id: Optional[int] = None
    team_name: str
    manager: Optional[str] = None
    logo_path: Optional[str] = None
    played: int = 0
    points: int = 0
    goal_difference: int = 0


class HomeDashboardTeamResponse(BaseModel):
    team_id: int
    team_name: str
    manager: str = ""
    level: str
    logo_path: Optional[str] = None
    next_match: Optional[HomeDashboardMatchResponse] = None
    recent_result: Optional[HomeDashboardMatchResponse] = None


class HomePromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_type: Literal["announcement", "honor", "update", "event"] = "announcement"
    theme: Literal["violet", "blue", "green", "gold", "rose", "neutral"] = "violet"
    icon: Literal["megaphone", "trophy", "list", "star", "whistle", "info"] = "megaphone"
    eyebrow: str = "HEIGO Broadcast"
    title: str
    body: str = ""
    image_url: Optional[str] = None
    action_label: Optional[str] = None
    action_kind: Literal["none", "tab", "url"] = "none"
    action_target: Optional[str] = None
    display_mode: Literal["board", "modal", "both"] = "board"
    is_active: bool = True
    is_pinned: bool = False
    is_dismissible: bool = True
    sort_order: int = 100
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    source_type: str = "custom"
    source_key: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuthStatusResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    role: Optional[str] = None
    can_manage_admin: bool = False
    can_manage_schedule: bool = False
    can_manage_cup_standings: bool = False
    can_manage_rankings: bool = False
    can_manage_suspensions: bool = False
    can_manage_candidate_lists: bool = False


class WorkspaceIdentityResponse(BaseModel):
    principal_id: str
    source: Literal["admin_account", "coach_account"]
    account_type: Literal["administrator", "worker", "coach", "coach_worker"]
    username: str
    qq_number: Optional[str] = None
    display_name: str
    role: Optional[str] = None
    coach_uid: Optional[str] = None
    team_name: Optional[str] = None
    is_full_admin: bool = False
    capabilities: list[str] = Field(default_factory=list)
    capability_labels: list[str] = Field(default_factory=list)


class WorkspaceSessionResponse(BaseModel):
    authenticated: bool = False
    identity: Optional[WorkspaceIdentityResponse] = None


class WorkspaceMetricResponse(BaseModel):
    key: str
    label: str
    value: int = 0
    detail: str = ""
    target_tab: Optional[str] = None
    target_subtab: Optional[str] = None


class WorkspaceRecentActionResponse(BaseModel):
    id: int
    summary: str
    status: str
    category: str
    created_at: Optional[datetime] = None


class WorkspaceTaskResponse(BaseModel):
    level: str
    round_start: int
    round_label: str
    status: str
    status_label: str
    assignee_principal_id: Optional[str] = None
    assignee_display_name: Optional[str] = None
    is_mine: bool = False
    responsibility_labels: list[str] = Field(default_factory=list)
    pending_count: int = 0
    target_subtab: str = "schedule"


class DataStatusItemResponse(BaseModel):
    key: str
    label: str
    scope: str = "all"
    status: Literal["normal", "pending", "stale", "error", "unknown"] = "unknown"
    status_label: str = "状态未知"
    updated_round: Optional[int] = None
    latest_round: Optional[int] = None
    completed_count: int = 0
    total_count: int = 0
    issue_count: int = 0
    data_version: Optional[str] = None
    source: Optional[str] = None
    updated_at: Optional[datetime] = None
    message: str = ""
    target_tab: str
    target_subtab: Optional[str] = None
    target_level: Optional[str] = None


class DataStatusResponse(BaseModel):
    generated_at: datetime
    items: list[DataStatusItemResponse] = Field(default_factory=list)


class HomeDashboardResponse(BaseModel):
    generated_at: datetime
    league_statuses: list[DataStatusItemResponse] = Field(default_factory=list)
    recent_results: list[HomeDashboardMatchResponse] = Field(default_factory=list)
    leaders: list[HomeDashboardLeaderResponse] = Field(default_factory=list)
    team: Optional[HomeDashboardTeamResponse] = None


class WorkspaceDashboardResponse(BaseModel):
    identity: WorkspaceIdentityResponse
    metrics: list[WorkspaceMetricResponse] = Field(default_factory=list)
    tasks: list[WorkspaceTaskResponse] = Field(default_factory=list)
    data_statuses: list[DataStatusItemResponse] = Field(default_factory=list)
    recent_actions: list[WorkspaceRecentActionResponse] = Field(default_factory=list)


class CompetitionWorkTaskResponse(BaseModel):
    match_id: int
    level: str
    round_no: int
    home_team_name: str
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str
    issue_codes: list[str] = Field(default_factory=list)
    issue_messages: list[str] = Field(default_factory=list)


class CompetitionWorkLogResponse(BaseModel):
    id: int
    action: str
    action_label: str
    operator_principal_id: str
    operator_display_name: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    detail: str = ""
    created_at: Optional[datetime] = None


class CompetitionResponsibilityResponse(BaseModel):
    level: str
    schedule_principal_id: Optional[str] = None
    schedule_display_name: Optional[str] = None
    suspension_principal_id: Optional[str] = None
    suspension_display_name: Optional[str] = None


class CompetitionRoundWorkSummaryResponse(BaseModel):
    level: str
    round_start: int
    round_end: int
    round_label: str
    workflow_status: str = "unassigned"
    workflow_status_label: str = "待任命"
    schedule_principal_id: Optional[str] = None
    schedule_display_name: Optional[str] = None
    suspension_principal_id: Optional[str] = None
    suspension_display_name: Optional[str] = None
    is_my_schedule_task: bool = False
    is_my_suspension_task: bool = False
    can_confirm_suspensions: bool = False
    assignee_principal_id: Optional[str] = None
    assignee_display_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    changed_after_submission: bool = False
    is_mine: bool = False
    can_submit: bool = False
    can_review: bool = False
    total_matches: int = 0
    result_ready_count: int = 0
    event_ready_count: int = 0
    missing_result_count: int = 0
    missing_event_count: int = 0
    invalid_count: int = 0
    suspension_confirmed: bool = False
    suspension_confirmed_at: Optional[datetime] = None
    suspension_confirmed_by: Optional[str] = None
    completion_ready: bool = False
    completed: bool = False
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    changed_after_completion: bool = False
    note: str = ""
    tasks: list[CompetitionWorkTaskResponse] = Field(default_factory=list)
    history: list[CompetitionWorkLogResponse] = Field(default_factory=list)


class CompetitionWorkSummaryResponse(BaseModel):
    levels: list[CompetitionRoundWorkSummaryResponse] = Field(default_factory=list)


class WorkspaceAccountResponse(BaseModel):
    principal_id: str
    source: Literal["admin_account", "coach_account"]
    account_type: Literal["administrator", "worker", "coach", "coach_worker"]
    username: Optional[str] = None
    qq_number: Optional[str] = None
    display_name: str
    coach_uid: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    level: Optional[str] = None
    is_active: bool = False
    must_change_password: bool = False
    role: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    last_login_at: Optional[datetime] = None


class WorkspaceAccountsResponse(BaseModel):
    items: list[WorkspaceAccountResponse] = Field(default_factory=list)


class LogsResponse(BaseModel):
    logs: str


class SchemaBootstrapStatusResponse(BaseModel):
    log_path: str
    file_exists: bool
    latest_event: Optional[str] = None
    recent_events: list[str]


class OperationAuditResponse(BaseModel):
    id: int
    category: str
    action: str
    operation_label: Optional[str] = None
    status: str
    source: str
    operator: Optional[str] = None
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class ProjectUpdateSectionResponse(BaseModel):
    heading: str
    items: list[str] = Field(default_factory=list)


class ProjectUpdateEntryResponse(BaseModel):
    version: str
    release_date: Optional[str] = None
    is_unreleased: bool = False
    sections: list[ProjectUpdateSectionResponse] = Field(default_factory=list)


class DataFeedbackReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_uid: Optional[int] = None
    player_name: Optional[str] = None
    issue_type: str
    summary: str
    details: str
    suggested_correction: Optional[str] = None
    contact: Optional[str] = None
    source_page: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class DataFeedbackSubmitResponse(BaseModel):
    success: bool
    report_id: int
    message: str
    status: str


class PlayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: int
    name: str
    age: int
    initial_ca: int
    ca: int
    pa: int
    position: str
    nationality: str
    team_name: str
    wage: float
    slot_type: str


class TeamStatRefreshStateResponse(BaseModel):
    cached_read_mode: Literal["cache_hit"]
    realtime_read_mode: Literal["realtime_overlay"]
    last_cache_refresh_mode: Literal["unknown", "full_recalc", "targeted_recalc", "write_incremental"]
    cached_read_label: str
    realtime_read_label: str
    last_cache_refresh_label: str
    last_cache_refresh_summary: str
    last_cache_refresh_at: Optional[datetime] = None
    last_cache_refresh_scopes: list[str]


class TeamStatSourcesResponse(BaseModel):
    cached_fields: list[str]
    realtime_fields: list[str]
    field_modes: dict[str, Literal["cached", "realtime"]]
    refresh_state: TeamStatRefreshStateResponse


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    manager: str
    level: str
    logo_path: Optional[str] = None
    wage: float
    team_size: int
    gk_count: int
    extra_wage: float = 0
    wage_cap: Optional[float] = None
    after_tax: float = 0
    final_wage: float
    count_8m: int
    count_7m: int
    count_fake: int
    total_value: float
    avg_value: float
    avg_ca: float
    avg_pa: float
    total_growth: int
    notes: Optional[str]
    stat_sources: TeamStatSourcesResponse


class TeamLineupResponse(BaseModel):
    team_id: int
    team_name: str
    formation: str = "4-3-3"
    picks: dict[str, int] = Field(default_factory=dict)
    is_saved: bool = False
    can_edit: bool = False
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class MatchPlayerEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    team_id: Optional[int] = None
    team_name: str
    player_uid: Optional[int] = None
    player_name: str
    event_type: Literal["goal", "own_goal", "assist", "mvp"]
    quantity: int = 1


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season_label: Optional[str] = None
    level: str
    round_no: int
    home_team_id: Optional[int] = None
    home_team_name: str
    away_team_id: Optional[int] = None
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: Literal["scheduled", "played", "postponed", "cancelled", "home_forfeit", "away_forfeit", "double_forfeit"]
    match_date: Optional[datetime] = None
    notes: Optional[str] = None
    source_file: Optional[str] = None
    updated_at: Optional[datetime] = None
    events: list[MatchPlayerEventResponse] = Field(default_factory=list)


class ScheduleResponse(BaseModel):
    levels: list[str] = Field(default_factory=list)
    rounds: list[int] = Field(default_factory=list)
    matches: list[MatchResponse] = Field(default_factory=list)


class CupMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition: str
    stage: str
    slot_no: int
    home_team_id: Optional[int] = None
    home_team_name: Optional[str] = None
    away_team_id: Optional[int] = None
    away_team_name: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    winner_team_id: Optional[int] = None
    winner_team_name: Optional[str] = None
    home_advancement: Literal["pending", "winner", "eliminated"] = "pending"
    away_advancement: Literal["pending", "winner", "eliminated"] = "pending"
    status: Literal["scheduled", "played"]
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class CupBracketResponse(BaseModel):
    competition: str
    title: str
    trophy_url: str
    stages: list[dict[str, Any]] = Field(default_factory=list)


class CupGroupSlotResponse(BaseModel):
    slot_no: int
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    manager: Optional[str] = None
    level: Optional[str] = None
    logo_path: Optional[str] = None


class CupGroupMatchResponse(BaseModel):
    id: int
    round_no: int
    slot_no: int
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: Literal["scheduled", "played"] = "scheduled"
    updated_at: Optional[datetime] = None


class CupGroupStandingResponse(BaseModel):
    rank: int
    team_id: int
    team_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    qualification: Literal["champions_knockout", "league_knockout", "eliminated", "pending"] = "pending"
    qualification_label: str = "待定"
    qualification_provisional: bool = True


class CupQualifiedTeamResponse(BaseModel):
    team_id: int
    team_name: str
    source_competition: str
    group_name: str
    group_rank: int
    points: int = 0
    goal_difference: int = 0
    goals_for: int = 0


class CupGroupResponse(BaseModel):
    group_no: int
    group_name: str
    teams: list[CupGroupSlotResponse] = Field(default_factory=list)
    matches: list[CupGroupMatchResponse] = Field(default_factory=list)
    standings: list[CupGroupStandingResponse] = Field(default_factory=list)


class CupGroupStageResponse(BaseModel):
    competition: str
    title: str
    group_count: int
    teams_per_group: int
    assigned_team_count: int = 0
    groups: list[CupGroupResponse] = Field(default_factory=list)
    qualification_complete: bool = False
    champions_knockout_qualifiers: list[CupQualifiedTeamResponse] = Field(default_factory=list)
    league_knockout_qualifiers: list[CupQualifiedTeamResponse] = Field(default_factory=list)


class TeamCupOpponentProgressResponse(BaseModel):
    team_id: int
    team_name: str
    played_legs: int = 0
    remaining_legs: int = 0


class TeamCupFixtureResponse(BaseModel):
    id: int
    stage: str
    stage_label: str
    round_no: Optional[int] = None
    opponent_team_id: Optional[int] = None
    opponent_team_name: str
    is_home: bool
    home_team_name: str
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: Literal["scheduled", "played"] = "scheduled"


class TeamCupCompetitionOutlookResponse(BaseModel):
    competition: str
    title: str
    theme: str
    phase: Literal["group", "knockout"]
    group_name: Optional[str] = None
    rank: Optional[int] = None
    played: int = 0
    points: int = 0
    goal_difference: int = 0
    qualification: str = "pending"
    qualification_label: str = "待定"
    qualification_provisional: bool = True
    qualification_context: str = ""
    remaining_match_count: int = 0
    remaining_opponent_count: int = 0
    opponents: list[TeamCupOpponentProgressResponse] = Field(default_factory=list)
    next_matches: list[TeamCupFixtureResponse] = Field(default_factory=list)


class TeamCupOutlookResponse(BaseModel):
    team_id: int
    team_name: str
    competitions: list[TeamCupCompetitionOutlookResponse] = Field(default_factory=list)


class StandingRowResponse(BaseModel):
    level: str
    rank: int
    team_id: Optional[int] = None
    team_name: str
    manager: Optional[str] = None
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    goal_rate: float = 0.0
    win_rate: float = 0.0
    home_played: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    home_goals_for: int = 0
    home_goals_against: int = 0
    home_goal_difference: int = 0
    home_points: int = 0
    home_win_rate: float = 0.0
    away_played: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
    away_goals_for: int = 0
    away_goals_against: int = 0
    away_goal_difference: int = 0
    away_points: int = 0
    away_win_rate: float = 0.0


class StandingsResponse(BaseModel):
    levels: list[str] = Field(default_factory=list)
    rows: list[StandingRowResponse] = Field(default_factory=list)


class PlayerRankingRowResponse(BaseModel):
    rank: int
    level: str
    player_uid: Optional[int] = None
    player_name: str
    team_id: Optional[int] = None
    team_name: str
    goals: int = 0
    assists: int = 0
    mvps: int = 0
    appearances: int = 0


class PlayerRankingCoverageResponse(BaseModel):
    level: str
    played_matches: int = 0
    matches_with_events: int = 0
    matches_missing_events: int = 0
    event_rows: int = 0
    goal_quantity: int = 0
    assist_quantity: int = 0
    mvp_quantity: int = 0


class PlayerRankingsResponse(BaseModel):
    levels: list[str] = Field(default_factory=list)
    rows: list[PlayerRankingRowResponse] = Field(default_factory=list)
    coverage: list[PlayerRankingCoverageResponse] = Field(default_factory=list)


class RankingStandingRowResponse(BaseModel):
    rank: int
    team_id: int
    team_name: str
    level: str
    logo_path: Optional[str] = None
    base_points: float = 1000.0
    total_points: float = 1000.0
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0


class RankingMatchResponse(BaseModel):
    id: int
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    result: Literal["home", "draw", "away"]
    played_at: datetime


class RankingsResponse(BaseModel):
    initial_points: float = 1000.0
    appearance_bonus: float = 20.0
    transfer_rate: float = 0.1
    total_matches: int = 0
    rows: list[RankingStandingRowResponse] = Field(default_factory=list)
    matches: list[RankingMatchResponse] = Field(default_factory=list)


class SuspensionPlayerResponse(BaseModel):
    player_uid: int
    player_name: str
    team_id: Optional[int] = None
    team_name: str
    level: str
    yellow_cards: int = 0
    red_card_suspended: bool = False
    red_injury_suspended: bool = False
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class SuspensionProgressResponse(BaseModel):
    state: Literal["current", "ahead", "stale", "gap", "unknown"]
    title: str
    detail: str
    match_completed_round: int = 0
    match_latest_recorded_round: int = 0
    match_continuous_completed_round: int = 0
    match_gap_rounds: list[int] = Field(default_factory=list)
    suspension_checked_round: Optional[int] = None
    applies_from_round: Optional[int] = None
    progress_floor_round: int = 0
    next_match_id: Optional[int] = None
    next_match_round: Optional[int] = None
    next_match_is_postponed: bool = False
    next_match_is_gap: bool = False
    marker_source: Optional[Literal["team", "level"]] = None


class SuspensionTeamResponse(BaseModel):
    team_id: int
    team_name: str
    manager: Optional[str] = None
    level: str
    is_orphaned: bool = False
    one_yellow: list[SuspensionPlayerResponse] = Field(default_factory=list)
    two_yellows: list[SuspensionPlayerResponse] = Field(default_factory=list)
    suspended: list[SuspensionPlayerResponse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    progress: Optional[SuspensionProgressResponse] = None


class SuspensionsResponse(BaseModel):
    levels: list[str] = Field(default_factory=list)
    teams: list[SuspensionTeamResponse] = Field(default_factory=list)


class LeagueInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str
    category: str


class TransferLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_uid: Optional[int] = None
    player_name: Optional[str] = None
    from_team_id: Optional[int] = None
    from_team: Optional[str] = None
    to_team_id: Optional[int] = None
    to_team: Optional[str] = None
    operation: Optional[str] = None
    ca_change: Optional[int] = None
    pa_change: Optional[int] = None
    age_change: Optional[int] = None
    operator: Optional[str] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None


class TeamInfoResponse(BaseModel):
    id: int
    name: str
    manager: Optional[str] = None
    level: str
    wage: float
    wage_cap: Optional[float] = None
    notes: Optional[str] = None


class AttributeSearchResponse(BaseModel):
    uid: int
    name: str
    data_version: str
    position: str
    age: int
    ca: int
    pa: int
    nationality: str
    club: str
    heigo_club: str
    weighted_power: Optional[float] = None
    heigo_power: Optional[float] = None
    top_percent: Optional[float] = None


class AdvancedAttributeSearchResponse(BaseModel):
    items: list[AttributeSearchResponse] = Field(default_factory=list)
    data_version: str
    limit: int
    truncated: bool = False
    applied_filters_summary: list[str] = Field(default_factory=list)


class AttributeBatchLookupResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    unmatched: list[str] = Field(default_factory=list)
    data_version: str
    token_count: int = 0


class CandidateListSummaryResponse(BaseModel):
    id: int
    name: str
    description: str = ""
    type: str = "custom"
    status: str = "draft"
    base_data_version: str = ""
    player_count: int = 0
    published_player_count: int = 0
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None
    archived_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None


class CandidateListDetailResponse(CandidateListSummaryResponse):
    source_filters: dict[str, Any] = Field(default_factory=dict)
    last_published_snapshot: dict[str, Any] = Field(default_factory=dict)


class CandidateListPlayerResponse(BaseModel):
    uid: int
    data_version: str
    name: str
    position: str = ""
    age: Optional[int] = None
    ca: Optional[int] = None
    pa: Optional[int] = None
    nationality: str = ""
    club: str = ""
    heigo_club: str = ""
    missing: bool = False
    added_at: Optional[datetime] = None


class CandidateListPlayersResponse(BaseModel):
    list_id: int
    name: str
    data_version: str
    total_count: int
    matched_count: int
    missing_count: int
    limit: int
    offset: int
    items: list[CandidateListPlayerResponse] = Field(default_factory=list)


class CandidateListPreviewCandidateResponse(BaseModel):
    uid: int
    name: str
    data_version: str
    position: str = ""
    age: Optional[int] = None
    ca: Optional[int] = None
    pa: Optional[int] = None
    club: str = ""
    heigo_club: str = ""


class CandidateListPreviewTokenResponse(BaseModel):
    token: str
    candidates: list[CandidateListPreviewCandidateResponse] = Field(default_factory=list)


class CandidateListPlayerPreviewResponse(BaseModel):
    matched: list[CandidateListPreviewCandidateResponse] = Field(default_factory=list)
    ambiguous: list[CandidateListPreviewTokenResponse] = Field(default_factory=list)
    unmatched: list[str] = Field(default_factory=list)
    already_exists: list[CandidateListPreviewCandidateResponse] = Field(default_factory=list)
    will_add_count: int = 0
    data_version: str = ""


class CandidateListRemovePreviewResponse(BaseModel):
    matched: list[CandidateListPlayerResponse] = Field(default_factory=list)
    ambiguous: list[CandidateListPreviewTokenResponse] = Field(default_factory=list)
    unmatched: list[str] = Field(default_factory=list)
    not_in_list: list[CandidateListPreviewCandidateResponse] = Field(default_factory=list)
    will_remove_count: int = 0
    data_version: str = ""


class CandidateListMutationResponse(BaseModel):
    success: bool = True
    message: str = ""
    list: Optional[CandidateListDetailResponse] = None
    preview: Optional[CandidateListPlayerPreviewResponse] = None
    added_count: int = 0
    removed_count: int = 0


class CandidateListPublishPreviewResponse(BaseModel):
    list_id: int
    name: str
    previous_count: int = 0
    current_count: int = 0
    added_uids: list[int] = Field(default_factory=list)
    removed_uids: list[int] = Field(default_factory=list)
    kept_count: int = 0
    missing_count: int = 0


class PositionScoreResponse(BaseModel):
    position: str
    score: int


class PlayerRadarMetricResponse(BaseModel):
    label: str
    value: float


class PlayerReactionSummaryResponse(BaseModel):
    flowers: int = 0
    eggs: int = 0
    can_react: bool = True
    cooldown_seconds: int = 0
    next_available_at: Optional[datetime] = None


class PlayerReactionActionResponse(BaseModel):
    accepted: bool
    reaction_type: Literal["flower", "egg"]
    message: str
    summary: PlayerReactionSummaryResponse


class CoachHonorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coach_uid: str
    edition: Optional[int] = None
    season: Optional[str] = None
    competition: Optional[str] = None
    placement: Optional[str] = None
    honor: str
    description: Optional[str] = None
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CoachAssistantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coach_uid: str
    name: str
    level: str
    note: Optional[str] = None
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CoachAccountPublicResponse(BaseModel):
    authenticated: bool = False
    coach_uid: Optional[str] = None
    username: Optional[str] = None
    qq_number: Optional[str] = None
    nickname: Optional[str] = None
    avatar_path: Optional[str] = None
    level: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    must_change_password: bool = False
    can_manage_schedule: bool = False
    can_manage_cup_standings: bool = False
    can_manage_rankings: bool = False
    can_manage_suspensions: bool = False
    can_manage_candidate_lists: bool = False


class CoachAccountAdminResponse(BaseModel):
    exists: bool = False
    username: Optional[str] = None
    qq_number: Optional[str] = None
    is_active: bool = False
    must_change_password: bool = False
    can_manage_schedule: bool = False
    can_manage_cup_standings: bool = False
    can_manage_rankings: bool = False
    can_manage_suspensions: bool = False
    can_manage_candidate_lists: bool = False
    last_login_at: Optional[datetime] = None


class CoachListItemResponse(BaseModel):
    uid: str
    nickname: str
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    level: Optional[str] = None
    avatar_path: Optional[str] = None
    title: Optional[str] = None
    title_color: Optional[str] = "white"
    bio: Optional[str] = None
    reaction_summary: PlayerReactionSummaryResponse = Field(default_factory=PlayerReactionSummaryResponse)


class CoachesResponse(BaseModel):
    levels: list[str] = Field(default_factory=list)
    coaches: list[CoachListItemResponse] = Field(default_factory=list)


class CoachDetailResponse(CoachListItemResponse):
    honors: list[CoachHonorResponse] = Field(default_factory=list)
    assistants: list[CoachAssistantResponse] = Field(default_factory=list)
    account: Optional[CoachAccountAdminResponse] = None
    updated_at: Optional[datetime] = None


class CoachReactionActionResponse(PlayerReactionActionResponse):
    pass


class PlayerReactionLeaderboardItemResponse(BaseModel):
    uid: int
    name: str
    data_version: str
    position: str
    age: int
    ca: int
    pa: int
    heigo_club: str
    flowers: int = 0
    eggs: int = 0
    net_score: int = 0
    total_reactions: int = 0
    updated_at: Optional[datetime] = None


class PlayerReactionLeaderboardResponse(BaseModel):
    metric: Literal["flowers", "eggs", "net"]
    limit: int
    team: Optional[str] = None
    data_version: str
    items: list[PlayerReactionLeaderboardItemResponse] = Field(default_factory=list)


class PlayerPowerRankingItemResponse(BaseModel):
    rank: int
    uid: int
    name: str
    display_name: str
    growth_step: int = 0
    ca_gain: int = 0
    ca: int
    projected_ca: int
    pa: int
    potential_gap: int = 0
    position: str
    weighted_power: float
    heigo_power: float
    top_percent: float
    heigo_club: str
    club: str
    data_version: str


class PlayerPowerRankingResponse(BaseModel):
    shape: Literal["all", "current", "1", "2", "3", "4", "5"] = "all"
    limit: int | Literal["all"]
    team: Optional[str] = None
    data_version: str
    items: list[PlayerPowerRankingItemResponse] = Field(default_factory=list)


class TeamPowerSummaryItemResponse(BaseModel):
    team_id: int
    team_name: str
    level: str
    roster_average: Optional[float] = None
    roster_rank: Optional[int] = None
    roster_player_count: int = 0
    lineup_average: Optional[float] = None
    lineup_rank: Optional[int] = None
    lineup_player_count: int = 0


class TeamPowerSummariesResponse(BaseModel):
    data_version: str
    items: list[TeamPowerSummaryItemResponse] = Field(default_factory=list)


class PlayerPowerCalibrationResponse(BaseModel):
    data_version: str
    player_count: int
    median_score: float
    mad: float
    robust_scale: float
    sorted_scores: list[float] = Field(default_factory=list)


class PlayerAttributeDetailResponse(BaseModel):
    uid: int
    name: str
    data_version: str
    position: str
    age: int
    ca: int
    pa: int
    nationality: str
    club: str
    heigo_club: str
    height: int
    weight: int
    left_foot: int
    right_foot: int
    radar_defense: float
    radar_physical: float
    radar_speed: float
    radar_creativity: float
    radar_attack: float
    radar_technical: float
    radar_aerial: float
    radar_mental: float
    birth_date: Optional[str] = None
    national_caps: int
    national_goals: int
    player_habits: Optional[str] = None
    player_habits_raw_code: Optional[str] = None
    player_habits_high_bits: Optional[str] = None
    corner: int
    crossing: int
    dribbling: int
    finishing: int
    first_touch: int
    free_kick: int
    heading: int
    long_shots: int
    long_throws: int
    marking: int
    passing: int
    penalty: int
    tackling: int
    technique: int
    aggression: int
    anticipation: int
    bravery: int
    composure: int
    concentration: int
    decisions: int
    determination: int
    flair: int
    leadership: int
    off_the_ball: int
    positioning: int
    teamwork: int
    vision: int
    work_rate: int
    acceleration: int
    agility: int
    balance: int
    jumping: int
    natural_fitness: int
    pace: int
    stamina: int
    strength: int
    consistency: int
    dirtiness: int
    important_matches: int
    injury_proneness: int
    versatility: int
    adaptability: int
    ambition: int
    controversy: int
    loyalty: int
    pressure: int
    professionalism: int
    sportsmanship: int
    temperament: int
    aerial_ability: int
    command_of_area: int
    communication: int
    eccentricity: int
    handling: int
    kicking: int
    one_on_ones: int
    reflexes: int
    rushing_out: int
    tendency_to_punch: int
    throwing: int
    pos_gk: int
    pos_dl: int
    pos_dc: int
    pos_dr: int
    pos_wbl: int
    pos_wbr: int
    pos_dm: int
    pos_ml: int
    pos_mc: int
    pos_mr: int
    pos_aml: int
    pos_amc: int
    pos_amr: int
    pos_st: int
    top_positions: list[PositionScoreResponse]
    radar_profile: list[PlayerRadarMetricResponse]
    reaction_summary: PlayerReactionSummaryResponse = Field(default_factory=PlayerReactionSummaryResponse)


class AttributeVersionsResponse(BaseModel):
    available_versions: list[str] = Field(default_factory=list)
    default_version: str
    default_version_player_count: int = 0


class SiteNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    text: str = ""
    round_no: Optional[int] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class WageDetailResponse(BaseModel):
    initial_value: float
    current_value: float
    potential_value: float
    final_value: float
    initial_field: float
    slot_type: str
    coefficient: float
    wage: float


class TeamExportRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    level: str = Field(alias="级别")
    team_name: str = Field(alias="球队名")
    manager: str = Field(alias="主教")
    team_size: int = Field(alias="球队人数")
    gk_count: int = Field(alias="门将人数")
    extra_wage: float = Field(alias="额外工资")
    wage_cap: float = Field(alias="工资帽")
    after_tax: float = Field(alias="税后")
    final_wage: float = Field(alias="最终工资")
    count_8m: int = Field(alias="8M")
    count_7m: int = Field(alias="7M")
    count_fake: int = Field(alias="伪名")
    total_value: float = Field(alias="总身价")
    avg_value: float = Field(alias="平均身价")
    avg_ca: float = Field(alias="平均CA")
    avg_pa: float = Field(alias="平均PA")
    total_growth: int = Field(alias="成长总计")
    notes: str = Field(alias="备注")


class PlayerExportRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    uid: int = Field(alias="编号")
    name: str = Field(alias="姓名")
    age: int = Field(alias="年龄")
    initial_ca: int = Field(alias="初始CA")
    ca: int = Field(alias="当前CA")
    pa: int = Field(alias="PA")
    position: str = Field(alias="位置")
    nationality: str = Field(alias="国籍")
    team_name: str = Field(alias="俱乐部")
    wage: float = Field(alias="工资")
    slot_type: str = Field(alias="名额")
