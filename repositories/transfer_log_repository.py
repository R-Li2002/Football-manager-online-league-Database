from sqlalchemy.orm import Session

from models import TransferLog


def get_transfer_log_by_id(db: Session, log_id: int) -> TransferLog | None:
    return db.query(TransferLog).filter(TransferLog.id == log_id).first()


def list_recent_transfer_logs(db: Session, limit: int = 100) -> list[TransferLog]:
    return db.query(TransferLog).order_by(TransferLog.created_at.desc()).limit(limit).all()


def update_player_uid_references(db: Session, old_uid: int, new_uid: int) -> None:
    db.query(TransferLog).filter(TransferLog.player_uid == old_uid).update({TransferLog.player_uid: new_uid})
