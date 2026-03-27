from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import DataFeedbackReport
from repositories.data_feedback_repository import create_data_feedback_report, list_data_feedback_reports
from schemas_read import DataFeedbackReportResponse, DataFeedbackSubmitResponse
from schemas_write import DataFeedbackRequest


def _normalize_optional_text(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def submit_data_feedback(db: Session, request: DataFeedbackRequest) -> DataFeedbackSubmitResponse:
    if request.website:
        raise HTTPException(status_code=400, detail="invalid_feedback_payload")

    summary = str(request.summary or "").strip()
    details = str(request.details or "").strip()
    if not summary or not details:
        raise HTTPException(status_code=400, detail="summary_and_details_required")

    report = DataFeedbackReport(
        player_uid=request.player_uid,
        player_name=_normalize_optional_text(request.player_name),
        issue_type=request.issue_type,
        summary=summary,
        details=details,
        suggested_correction=_normalize_optional_text(request.suggested_correction),
        contact=_normalize_optional_text(request.contact),
        source_page=_normalize_optional_text(request.source_page),
        status="open",
        created_at=datetime.now(),
    )
    persisted = create_data_feedback_report(db, report)
    return DataFeedbackSubmitResponse(
        success=True,
        report_id=persisted.id,
        message="感谢反馈，我们已收到这条数据纠错信息。",
        status=persisted.status,
    )


def get_data_feedback_reports(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[DataFeedbackReportResponse]:
    normalized_status = str(status or "").strip() or None
    reports = list_data_feedback_reports(db, status=normalized_status, limit=limit)
    return [DataFeedbackReportResponse.model_validate(report, from_attributes=True) for report in reports]
