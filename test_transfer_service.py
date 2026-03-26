from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from database import Base, init_database
from models import Player, Team, TransferLog
from services import league_service, transfer_service
from team_links import SEA_TEAM_NAME


class TransferServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "transfer_service.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", poolclass=NullPool)
        Base.metadata.create_all(bind=self.engine)
        init_database(target_engine=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _seed(self):
        alpha = Team(name="Alpha FC", manager="A", level="\u8d85\u7ea7", wage=0)
        beta = Team(name="Beta FC", manager="B", level="\u7532\u7ea7", wage=0)
        sea = Team(name=SEA_TEAM_NAME, manager="Sea", level="\u9690\u85cf", wage=0)
        self.db.add_all([alpha, beta, sea])
        self.db.flush()

        alpha_player = Player(
            uid=1001,
            name="Alpha One",
            age=22,
            initial_ca=100,
            ca=110,
            pa=125,
            position="MC",
            nationality="ENG",
            team_id=alpha.id,
            team_name=alpha.name,
            wage=0,
            slot_type="",
        )
        beta_player = Player(
            uid=1002,
            name="Beta One",
            age=21,
            initial_ca=98,
            ca=103,
            pa=120,
            position="ST",
            nationality="BRA",
            team_id=beta.id,
            team_name=beta.name,
            wage=0,
            slot_type="",
        )
        for player in (alpha_player, beta_player):
            league_service.refresh_player_financials(player, self.db)
            self.db.add(player)

        self.db.commit()
        league_service.recalculate_team_stats(self.db)

    def test_transfer_player_refreshes_affected_team_stats_and_logs(self):
        result = transfer_service.transfer_player(
            self.db,
            "HEIGO01",
            SimpleNamespace(player_uid=1001, to_team="Beta FC", notes="svc transfer"),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        moved_player = self.db.query(Player).filter(Player.uid == 1001).one()
        self.assertEqual(moved_player.team_name, "Beta FC")

        alpha = self.db.query(Team).filter(Team.name == "Alpha FC").one()
        beta = self.db.query(Team).filter(Team.name == "Beta FC").one()
        self.assertEqual(alpha.team_size, 0)
        self.assertEqual(beta.team_size, 2)
        self.assertEqual(alpha.stats_cache_refresh_mode, league_service.TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL)
        self.assertEqual(beta.stats_cache_refresh_mode, league_service.TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL)

        logs = self.db.query(TransferLog).filter(TransferLog.player_uid == 1001).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].operation, "\u4ea4\u6613")
        self.assertEqual(logs[0].from_team, "Alpha FC")
        self.assertEqual(logs[0].to_team, "Beta FC")

    def test_transfer_player_failure_does_not_create_transfer_log(self):
        with self.assertRaises(HTTPException):
            transfer_service.transfer_player(
                self.db,
                "HEIGO01",
                SimpleNamespace(player_uid=1001, to_team="Missing FC", notes="broken"),
                lambda *_args: None,
            )

        logs = self.db.query(TransferLog).filter(TransferLog.player_uid == 1001).all()
        self.assertEqual(logs, [])
        player = self.db.query(Player).filter(Player.uid == 1001).one()
        self.assertEqual(player.team_name, "Alpha FC")


if __name__ == "__main__":
    unittest.main()
