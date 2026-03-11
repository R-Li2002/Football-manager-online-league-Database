from sqlalchemy.orm import Session

from models import AdminUser


def get_admin_by_username(db: Session, username: str) -> AdminUser | None:
    return db.query(AdminUser).filter(AdminUser.username == username).first()
