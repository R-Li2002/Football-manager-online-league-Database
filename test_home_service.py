import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Player, Team
from services.home_service import get_home_summary


class HomeServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_summary_counts_only_public_league_data(self):
        self.session.add_all([
            Team(id=1, name="Visible FC", level="甲级"),
            Team(id=2, name="Hidden FC", level="隐藏"),
            Player(uid=101, name="Visible Player", team_name="Visible FC"),
            Player(uid=102, name="Sea Player", team_name="85大海"),
        ])
        self.session.commit()

        summary = get_home_summary(self.session)

        self.assertEqual(summary["team_count"], 1)
        self.assertEqual(summary["player_count"], 1)
        self.assertEqual(summary["database_player_count"], 0)
        self.assertIsInstance(summary["default_attribute_version"], str)


if __name__ == "__main__":
    unittest.main()
