from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None


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
    wage: float
    team_size: int
    gk_count: int
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
    notes: Optional[str] = None


class AttributeSearchResponse(BaseModel):
    uid: int
    name: str
    position: str
    age: int
    ca: int
    pa: int
    nationality: str
    club: str
    heigo_club: str


class PositionScoreResponse(BaseModel):
    position: str
    score: int


class PlayerAttributeDetailResponse(BaseModel):
    uid: int
    name: str
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
    birth_date: Optional[str] = None
    national_caps: int
    national_goals: int
    player_habits: Optional[str] = None
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
