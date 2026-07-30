import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services.site_visit_service import record_site_visit


class SiteVisitServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_records_today_and_total_counts(self):
        first = record_site_visit(self.session, visit_date="2026-07-17")
        second = record_site_visit(self.session, visit_date="2026-07-17")
        next_day = record_site_visit(self.session, visit_date="2026-07-18")

        self.assertEqual(first, {"total_count": 1, "today_count": 1, "visit_date": "2026-07-17"})
        self.assertEqual(second, {"total_count": 2, "today_count": 2, "visit_date": "2026-07-17"})
        self.assertEqual(next_day, {"total_count": 3, "today_count": 1, "visit_date": "2026-07-18"})


if __name__ == "__main__":
    unittest.main()
