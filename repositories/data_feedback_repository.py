from __future__ import annotations

from sqlalchemy.orm import Session

from models import DataFeedbackReport


def create_data_feedback_report(db: Session, report: DataFeedbackReport) -> DataFeedbackReport:
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_data_feedback_reports(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[DataFeedbackReport]:
    query = db.query(DataFeedbackReport)
    if status:
        query = query.filter(DataFeedbackReport.status == status)
    return (
        query.order_by(DataFeedbackReport.created_at.desc(), DataFeedbackReport.id.desc())
        .limit(limit)
        .all()
    )
