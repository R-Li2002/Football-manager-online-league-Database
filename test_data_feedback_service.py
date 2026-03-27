import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from database import Base, init_database
from schemas_write import DataFeedbackRequest
from services import admin_read_service, data_feedback_service


class DataFeedbackServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "data_feedback.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", poolclass=NullPool)
        Base.metadata.create_all(bind=self.engine)
        init_database(target_engine=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_submit_data_feedback_persists_open_report(self):
        result = data_feedback_service.submit_data_feedback(
            self.db,
            DataFeedbackRequest(
                player_uid=1001,
                player_name="Alpha One",
                issue_type="team_assignment",
                summary="球队归属不正确",
                details="当前显示为 Alpha FC，但应为 Beta FC。",
                suggested_correction="请改为 Beta FC",
                contact="qq:123456",
                source_page="/database?uid=1001",
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "open")

        reports = admin_read_service.get_recent_data_feedback_reports(self.db, limit=10)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].summary, "球队归属不正确")
        self.assertEqual(reports[0].player_uid, 1001)
        self.assertEqual(reports[0].suggested_correction, "请改为 Beta FC")


if __name__ == "__main__":
    unittest.main()
