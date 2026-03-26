from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from database import Base, init_database
from models import Player, Team, TransferLog
from services import league_service, roster_service


class RosterServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "roster_service.db"
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
        team = Team(name="Alpha FC", manager="A", level="\u8d85\u7ea7", wage=0)
        other = Team(name="Beta FC", manager="B", level="\u7532\u7ea7", wage=0)
        self.db.add_all([team, other])
        self.db.flush()

        player = Player(
            uid=1001,
            name="Alpha One",
            age=22,
            initial_ca=100,
            ca=110,
            pa=125,
            position="MC",
            nationality="ENG",
            team_id=team.id,
            team_name=team.name,
            wage=0,
            slot_type="",
        )
        league_service.refresh_player_financials(player, self.db)
        self.db.add(player)
        self.db.commit()
        league_service.recalculate_team_stats(self.db)

        self.db.add(
            TransferLog(
                player_uid=1001,
                player_name="Alpha One",
                from_team="Alpha FC",
                to_team="Alpha FC",
                operation="\u6d88\u8d39",
                operator="HEIGO01",
            )
        )
        self.db.commit()

    def test_consume_player_refreshes_team_stats(self):
        result = roster_service.consume_player(
            self.db,
            "HEIGO01",
            SimpleNamespace(player_uid=1001, ca_change=3, pa_change=0, notes="consume"),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        team_after = self.db.query(Team).filter(Team.name == "Alpha FC").one()
        self.assertEqual(team_after.stats_cache_refresh_mode, league_service.TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL)
        logs = self.db.query(TransferLog).filter(TransferLog.player_uid == 1001).order_by(TransferLog.id.asc()).all()
        self.assertEqual(logs[-1].operation, "\u6d88\u8d39")

    def test_update_team_info_keeps_player_team_link_consistent(self):
        result = roster_service.update_team_info(
            self.db,
            "HEIGO01",
            SimpleNamespace(team_name="Alpha FC", manager="Neo", name="Gamma FC", notes=None, level=None),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        team = self.db.query(Team).filter(Team.name == "Gamma FC").one()
        player = self.db.query(Player).filter(Player.uid == 1001).one()
        self.assertEqual(player.team_id, team.id)
        self.assertEqual(player.team_name, "Gamma FC")

    def test_update_player_uid_updates_transfer_log_references(self):
        result = roster_service.update_player_uid(
            self.db,
            "HEIGO01",
            SimpleNamespace(old_uid=1001, new_uid=2001),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        player = self.db.query(Player).filter(Player.uid == 2001).one()
        self.assertEqual(player.name, "Alpha One")
        logs = self.db.query(TransferLog).filter(TransferLog.player_uid == 2001).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].player_name, "Alpha One")


if __name__ == "__main__":
    unittest.main()
