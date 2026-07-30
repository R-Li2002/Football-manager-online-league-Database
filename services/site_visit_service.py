from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from models import SiteVisitStat

SITE_TIMEZONE = ZoneInfo("Asia/Shanghai")


def record_site_visit(db: Session, *, visit_date: str | None = None) -> dict[str, int | str]:
    date_key = visit_date or datetime.now(SITE_TIMEZONE).date().isoformat()

    if db.get_bind().dialect.name == "sqlite":
        statement = sqlite_insert(SiteVisitStat).values(visit_date=date_key, visit_count=1)
        statement = statement.on_conflict_do_update(
            index_elements=[SiteVisitStat.visit_date],
            set_={"visit_count": SiteVisitStat.visit_count + 1},
        )
        db.execute(statement)
    else:
        current = db.get(SiteVisitStat, date_key)
        if current is None:
            db.add(SiteVisitStat(visit_date=date_key, visit_count=1))
        else:
            current.visit_count += 1

    db.commit()

    today_count = db.query(SiteVisitStat.visit_count).filter(SiteVisitStat.visit_date == date_key).scalar() or 0
    total_count = db.query(func.coalesce(func.sum(SiteVisitStat.visit_count), 0)).scalar() or 0
    return {
        "total_count": int(total_count),
        "today_count": int(today_count),
        "visit_date": date_key,
    }
