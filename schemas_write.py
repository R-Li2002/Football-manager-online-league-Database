from typing import Any, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    username: str


class LogoutResponse(BaseModel):
    success: bool


class AdminActionResponse(BaseModel):
    success: bool
    message: str


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
    workbook_path: str = ""
    attributes_csv_path: str = ""
    backup_path: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    datasets: dict[str, ImportDatasetSummaryResponse] = Field(default_factory=dict)


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


class PlayerUpdateRequest(BaseModel):
    uid: int
    name: Optional[str] = None
    position: Optional[str] = None
    nationality: Optional[str] = None
    age: Optional[int] = None


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
    attributes: dict[str, AdvancedAttributeRangeRequest] = Field(default_factory=dict)
    positions: list[AdvancedAttributePositionRequest] = Field(default_factory=list)
    limit: int = 200
