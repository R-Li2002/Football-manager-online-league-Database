from sqlalchemy.orm import Session

from models import OperationAudit


def list_recent_operation_audits(db: Session, limit: int = 20, category: str | None = None) -> list[OperationAudit]:
    query = db.query(OperationAudit)
    if category:
        query = query.filter(OperationAudit.category == category)
    return query.order_by(OperationAudit.created_at.desc(), OperationAudit.id.desc()).limit(limit).all()


def list_operation_audits(db: Session, *, category: str | None = None, limit: int | None = None) -> list[OperationAudit]:
    query = db.query(OperationAudit)
    if category:
        query = query.filter(OperationAudit.category == category)
    query = query.order_by(OperationAudit.created_at.desc(), OperationAudit.id.desc())
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get_latest_operation_audit(
    db: Session,
    *,
    category: str,
    action: str | None = None,
    source: str | None = None,
) -> OperationAudit | None:
    query = db.query(OperationAudit).filter(OperationAudit.category == category)
    if action:
        query = query.filter(OperationAudit.action == action)
    if source:
        query = query.filter(OperationAudit.source == source)
    return query.order_by(OperationAudit.created_at.desc(), OperationAudit.id.desc()).first()
