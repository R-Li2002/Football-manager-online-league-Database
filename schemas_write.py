from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    username: str
    role: str = "admin"
    can_manage_admin: bool = False
    can_manage_schedule: bool = False
    can_manage_cup_standings: bool = False
    can_manage_rankings: bool = False
    can_manage_suspensions: bool = False
    can_manage_candidate_lists: bool = False
    can_manage_daily_reports: bool = False
    can_manage_draws: bool = False
    can_manage_archives: bool = False


class LogoutResponse(BaseModel):
    success: bool


class AdminActionResponse(BaseModel):
    success: bool
    message: str


class SuspensionRecordUpdateResponse(AdminActionResponse):
    record: Optional[dict[str, Any]] = None
    merged: bool = False
    merged_record_count: int = 0


class TeamLogoMatchApplyRequest(BaseModel):
    team_id: int
    slug: str
    matched_query: str
    source_name: str
    source_version: Optional[str] = None
    source_variant: Optional[str] = None
    matched_score: Optional[float] = None
    confirmed: bool = False


class HomePromotionUpsertRequest(BaseModel):
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


class DailyReportGenerateRequest(BaseModel):
    report_date: Optional[str] = None


class DailyReportUpdateRequest(BaseModel):
    title: str
    content: str
    publish: bool = False


class DailyReportNarrativeTemplateUpsertRequest(BaseModel):
    category: str
    name: str
    template_text: str
    is_active: bool = True
    sort_order: int = 100


class ImportDatasetSummaryResponse(BaseModel):
    source: str
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class AdminImportResponse(BaseModel):
    success: bool
    message: str
    committed: bool = False
    strict_mode: bool = True
    skip_attributes: bool = False
    workbook_path: str = ""
    attributes_csv_path: str = ""
    backup_path: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    datasets: dict[str, ImportDatasetSummaryResponse] = Field(default_factory=dict)


class ScheduleImportResponse(BaseModel):
    success: bool
    message: str
    source_file: str
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    warnings: list[str] = Field(default_factory=list)


class MatchPlayerEventUpdateItem(BaseModel):
    team_name: str
    player_uid: Optional[int] = None
    player_name: str
    event_type: str
    quantity: int = 1


class MatchUpdateRequest(BaseModel):
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: Optional[str] = None
    match_date: Optional[str] = None
    notes: Optional[str] = None
    events: list[MatchPlayerEventUpdateItem] = Field(default_factory=list)


class MatchBatchUpdateItem(BaseModel):
    match_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    events: list[MatchPlayerEventUpdateItem] = Field(default_factory=list)


class MatchBatchUpdateRequest(BaseModel):
    matches: list[MatchBatchUpdateItem]


class RankingMatchCreateRequest(BaseModel):
    home_team_id: int
    away_team_id: int
    result: Literal["home", "draw", "away"]


class RankingCutoffUpdateRequest(BaseModel):
    cutoff_floor: Optional[int] = Field(default=None, ge=1, le=1000000)


class CupMatchTeamsUpdateRequest(BaseModel):
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    notes: Optional[str] = None


class CupGroupUpdateRequest(BaseModel):
    team_ids: list[Optional[int]] = Field(default_factory=list)


class CupGroupMatchResultUpdateRequest(BaseModel):
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class CupMatchResultUpdateRequest(BaseModel):
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    winner_team_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    advancement_reason: Optional[Literal["away_goals", "extra_time", "penalties", "other"]] = None


class SuspensionRecordUpdateRequest(BaseModel):
    player_uid: int
    yellow_cards: int = 0
    yellow_card_suspended: bool = False
    red_card_suspended: bool = False
    red_injury_suspended: bool = False
    suspension_matches: int = Field(default=1, ge=1, le=99)
    notes: Optional[str] = None
    merge_existing: bool = False
    merge_base_yellow_cards: Optional[int] = None


class SiteNoteUpdateRequest(BaseModel):
    text: str = ""
    round_no: Optional[int] = None


class TeamLineupUpdateRequest(BaseModel):
    formation: str = "4-3-3"
    picks: dict[str, int] = Field(default_factory=dict)


class CoachUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    title: Optional[str] = None
    title_color: Optional[str] = None
    bio: Optional[str] = None


class CoachHonorUpdateRequest(BaseModel):
    coach_uid: Optional[str] = None
    edition: Optional[int] = None
    season: Optional[str] = None
    competition: Optional[str] = None
    placement: Optional[str] = None
    honor: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0


class CoachAssistantUpdateRequest(BaseModel):
    coach_uid: Optional[str] = None
    name: str
    level: str
    note: Optional[str] = None
    sort_order: int = 0


class CoachLoginRequest(BaseModel):
    username: str
    password: str


class CoachAccountUpsertRequest(BaseModel):
    username: str
    password: Optional[str] = None
    is_active: bool = True
    can_manage_schedule: bool = False
    can_manage_cup_standings: bool = False
    can_manage_rankings: bool = False
    can_manage_suspensions: bool = False
    can_manage_candidate_lists: bool = False
    can_manage_daily_reports: bool = False
    can_manage_draws: bool = False
    can_manage_archives: bool = False


class DrawPoolEntryRequest(BaseModel):
    team_id: Optional[int] = None
    player_uid: Optional[int] = None
    entity_name: Optional[str] = None
    team_name: Optional[str] = None
    level: Optional[str] = None
    source_rank: Optional[int] = None
    pot_no: Optional[int] = Field(default=None, ge=1, le=12)
    seed_status: Optional[Literal["seeded", "unseeded"]] = None
    self_save_count: int = Field(default=0, ge=0, le=20)
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class DrawSessionCreateRequest(BaseModel):
    name: str
    draw_type: Literal[
        "champions_group",
        "league_group",
        "champions_r16",
        "league_r16",
        "wumingjian_qualifying",
        "wumingjian_r32",
        "lottery",
        "custom_team",
        "custom_player",
    ]
    season_label: Optional[str] = None
    random_seed: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
    entries: list[DrawPoolEntryRequest] = Field(default_factory=list)


class DrawSessionUpdateRequest(BaseModel):
    name: Optional[str] = None
    season_label: Optional[str] = None
    random_seed: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    entries: Optional[list[DrawPoolEntryRequest]] = None


class DrawNextRequest(BaseModel):
    entry_id: int = Field(ge=1)


class LotteryPoolBuildRequest(BaseModel):
    min_final_value: float = Field(default=5.0, ge=0, le=50)
    team_ids: list[int] = Field(default_factory=list)
    excluded_candidate_list_ids: list[int] = Field(default_factory=list)
    excluded_player_uids: list[int] = Field(default_factory=list)
    restored_player_uids: list[int] = Field(default_factory=list)
    self_save_counts: dict[str, int] = Field(default_factory=dict)
    limit: int = Field(default=15, ge=1, le=100)


class DrawVoidRequest(BaseModel):
    reason: str


class DrawInvalidatePickRequest(BaseModel):
    reason: str


class SeasonArchiveCreateRequest(BaseModel):
    season_key: str
    title: Optional[str] = None
    confirm: bool = False
    revision_of: Optional[int] = None
    revision_reason: Optional[str] = None


class CoachTeamAssignmentRequest(BaseModel):
    team_id: Optional[int] = None


class CoachMergeRequest(BaseModel):
    target_coach_uid: str


class CoachPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class CoachQqBindingRequest(BaseModel):
    qq_number: str
    current_password: str


class CompetitionRoundConfirmationRequest(BaseModel):
    confirmed: bool = True
    note: Optional[str] = None


class CompetitionRoundAssignmentRequest(BaseModel):
    assignee_principal_id: Optional[str] = None


class CompetitionResponsibilityUpdateRequest(BaseModel):
    schedule_principal_id: Optional[str] = None
    suspension_principal_id: Optional[str] = None


class CompetitionRoundSubmissionRequest(BaseModel):
    note: Optional[str] = None


class CompetitionRoundReviewRequest(BaseModel):
    approved: bool = True
    note: Optional[str] = None


class BatchActionItemResponse(BaseModel):
    uid: int
    success: bool
    message: str


class BatchActionResponse(BaseModel):
    success: bool
    results: list[BatchActionItemResponse]
    success_count: int


class TransferRequest(BaseModel):
    player_uid: int
    to_team: str
    notes: Optional[str] = ""


class FishPlayerRequest(BaseModel):
    uid: int
    name: str
    age: int
    ca: int
    pa: int
    position: str
    nationality: str
    team_name: str
    wage: float
    slot_type: str
    notes: Optional[str] = ""


class ConsumeRequest(BaseModel):
    player_uid: int
    ca_change: int = 0
    pa_change: int = 0
    notes: Optional[str] = ""


class RejuvenateRequest(BaseModel):
    player_uid: int
    age_change: int
    notes: Optional[str] = ""


class BatchTransferItem(BaseModel):
    uid: int
    to_team: str
    notes: Optional[str] = ""


class BatchTransferRequest(BaseModel):
    items: list[BatchTransferItem]


class BatchConsumeItem(BaseModel):
    uid: int
    ca_change: int = 0
    pa_change: int = 0
    notes: Optional[str] = ""


class BatchConsumeRequest(BaseModel):
    items: list[BatchConsumeItem]


class BatchReleaseItem(BaseModel):
    uid: int
    notes: Optional[str] = ""


class BatchReleaseRequest(BaseModel):
    items: list[BatchReleaseItem]


class TeamUpdateRequest(BaseModel):
    team_name: str
    manager: Optional[str] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    level: Optional[str] = None
    wage_cap: Optional[float] = Field(default=None, gt=0, le=100)


class PlayerUpdateRequest(BaseModel):
    uid: int
    name: Optional[str] = None
    position: Optional[str] = None
    nationality: Optional[str] = None
    age: Optional[int] = None
    ca: Optional[int] = Field(default=None, ge=1, le=200)
    pa: Optional[int] = Field(default=None, ge=-10, le=200)


class UpdateUidRequest(BaseModel):
    old_uid: int
    new_uid: int


class DataFeedbackRequest(BaseModel):
    player_uid: Optional[int] = None
    player_name: Optional[str] = None
    issue_type: str
    summary: str
    details: str
    suggested_correction: Optional[str] = None
    contact: Optional[str] = None
    source_page: Optional[str] = None
    website: Optional[str] = ""


class AdvancedAttributeRangeRequest(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class AdvancedAttributePositionRequest(BaseModel):
    position: str
    min_score: int


class AdvancedAttributeSearchRequest(BaseModel):
    query: str = ""
    version: Optional[str] = None
    age: Optional[AdvancedAttributeRangeRequest] = None
    ca: Optional[AdvancedAttributeRangeRequest] = None
    pa: Optional[AdvancedAttributeRangeRequest] = None
    weighted_power: Optional[AdvancedAttributeRangeRequest] = None
    attributes: dict[str, AdvancedAttributeRangeRequest] = Field(default_factory=dict)
    positions: list[AdvancedAttributePositionRequest] = Field(default_factory=list)
    sea_status: Optional[Literal["in_sea", "not_in_sea"]] = None
    uids: list[int] = Field(default_factory=list)
    limit: int = 200


class AttributeBatchLookupRequest(BaseModel):
    tokens: list[str] = Field(default_factory=list)
    version: Optional[str] = None


class CandidateListUpsertRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str = "custom"
    base_data_version: Optional[str] = None
    source_filters: dict[str, Any] = Field(default_factory=dict)


class CandidateListPlayerPreviewRequest(BaseModel):
    tokens: list[str] = Field(default_factory=list)
    uids: list[int] = Field(default_factory=list)
    version: Optional[str] = None


class CandidateListPlayerCommitRequest(BaseModel):
    tokens: list[str] = Field(default_factory=list)
    uids: list[int] = Field(default_factory=list)
    confirmed_uids: list[int] = Field(default_factory=list)
    version: Optional[str] = None


class CandidateListBatchRemoveRequest(BaseModel):
    tokens: list[str] = Field(default_factory=list)
    uids: list[int] = Field(default_factory=list)
    version: Optional[str] = None
