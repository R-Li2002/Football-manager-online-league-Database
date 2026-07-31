from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from database import Base, init_database
from models import Player, PlayerAttribute, Team, TransferLog
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
        archive = Team(name="Archive", manager="Archive", level="\u9690\u85cf", wage=0)
        self.db.add_all([alpha, beta, sea, archive])
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
        sea_player = Player(
            uid=1003,
            name="Sea One",
            age=24,
            initial_ca=105,
            ca=118,
            pa=130,
            position="AMC",
            nationality="ESP",
            team_id=sea.id,
            team_name=sea.name,
            wage=0,
            slot_type="",
        )
        outside_player = Player(
            uid=1004,
            name="Outside One",
            age=23,
            initial_ca=102,
            ca=111,
            pa=126,
            position="DC",
            nationality="ITA",
            team_id=archive.id,
            team_name=archive.name,
            wage=0,
            slot_type="",
        )
        for player in (alpha_player, beta_player, sea_player, outside_player):
            league_service.refresh_player_financials(player, self.db)
            self.db.add(player)
        self.db.add(
            PlayerAttribute(
                uid=72048200,
                name="Miles Robinson",
                age=28,
                ca=134,
                pa=137,
                position="D C",
                nationality="United States",
                club="FC Cincinnati",
            )
        )

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

    def test_fish_sea_player_moves_existing_player_and_resets_current_ca(self):
        old_wage = self.db.query(Player).filter(Player.uid == 1003).one().wage

        result = transfer_service.fish_sea_player(
            self.db,
            "HEIGO01",
            SimpleNamespace(player_uid=1003, to_team="Alpha FC", notes="sea signing"),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        player = self.db.query(Player).filter(Player.uid == 1003).one()
        self.assertEqual(player.team_name, "Alpha FC")
        self.assertEqual(player.ca, 105)
        self.assertNotEqual(player.wage, old_wage)

        alpha = self.db.query(Team).filter(Team.name == "Alpha FC").one()
        sea = self.db.query(Team).filter(Team.name == SEA_TEAM_NAME).one()
        self.assertEqual(alpha.team_size, 2)
        self.assertEqual(sea.team_size, 0)
        self.assertEqual(alpha.stats_cache_refresh_mode, league_service.TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL)
        self.assertEqual(sea.level, "\u9690\u85cf")

        log = self.db.query(TransferLog).filter(TransferLog.player_uid == 1003).one()
        self.assertEqual(log.operation, "\u6d77\u635e")
        self.assertEqual(log.from_team, SEA_TEAM_NAME)
        self.assertEqual(log.to_team, "Alpha FC")
        self.assertEqual(log.ca_change, -13)

    def test_fish_sea_player_rejects_non_sea_player_and_hidden_target(self):
        with self.assertRaises(HTTPException) as non_sea_error:
            transfer_service.fish_sea_player(
                self.db,
                "HEIGO01",
                SimpleNamespace(player_uid=1001, to_team="Beta FC", notes=""),
                lambda *_args: None,
            )
        self.assertEqual(non_sea_error.exception.detail, transfer_service.PLAYER_NOT_IN_SEA)

        with self.assertRaises(HTTPException) as hidden_target_error:
            transfer_service.fish_sea_player(
                self.db,
                "HEIGO01",
                SimpleNamespace(player_uid=1003, to_team=SEA_TEAM_NAME, notes=""),
                lambda *_args: None,
            )
        self.assertEqual(hidden_target_error.exception.detail, transfer_service.INVALID_FISH_TARGET)

    def test_fish_sea_player_accepts_any_player_outside_three_league_levels(self):
        result = transfer_service.fish_sea_player(
            self.db,
            "HEIGO01",
            SimpleNamespace(player_uid=1004, to_team="Beta FC", notes="outside league"),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        player = self.db.query(Player).filter(Player.uid == 1004).one()
        self.assertEqual(player.team_name, "Beta FC")
        self.assertEqual(player.ca, player.initial_ca)
        log = self.db.query(TransferLog).filter(TransferLog.player_uid == 1004).one()
        self.assertEqual(log.from_team, SEA_TEAM_NAME)

    def test_fish_sea_player_can_create_roster_player_from_attribute_database(self):
        result = transfer_service.fish_sea_player(
            self.db,
            "HEIGO01",
            SimpleNamespace(player_uid=72048200, to_team="Alpha FC", notes=""),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        player = self.db.query(Player).filter(Player.uid == 72048200).one()
        self.assertEqual(player.name, "Miles Robinson")
        self.assertEqual(player.team_name, "Alpha FC")
        self.assertEqual(player.initial_ca, 134)
        self.assertEqual(player.ca, 134)
        self.assertEqual(player.pa, 137)
        self.assertGreater(player.wage, 0)
        log = self.db.query(TransferLog).filter(TransferLog.player_uid == 72048200).one()
        self.assertEqual(log.from_team, SEA_TEAM_NAME)
        self.assertEqual(log.notes, "从球员数据库海捞")

    def test_undo_sea_fish_returns_player_to_sea_and_restores_ca(self):
        transfer_service.fish_sea_player(
            self.db,
            "HEIGO01",
            SimpleNamespace(player_uid=1003, to_team="Alpha FC", notes="undo me"),
            lambda *_args: None,
        )
        log = self.db.query(TransferLog).filter(TransferLog.player_uid == 1003).one()

        result = transfer_service.undo_operation(self.db, "HEIGO01", log.id, lambda *_args: None)

        self.assertTrue(result["success"])
        player = self.db.query(Player).filter(Player.uid == 1003).one()
        self.assertEqual(player.team_name, SEA_TEAM_NAME)
        self.assertEqual(player.ca, 118)
        self.assertIsNone(self.db.query(TransferLog).filter(TransferLog.id == log.id).first())

    def test_undo_legacy_fish_still_deletes_created_player(self):
        transfer_service.fish_player(
            self.db,
            "HEIGO01",
            SimpleNamespace(
                uid=2001,
                name="Created One",
                age=20,
                ca=101,
                pa=125,
                position="ST",
                nationality="FRA",
                team_name="Alpha FC",
                notes="legacy fish",
            ),
            lambda *_args: None,
        )
        log = self.db.query(TransferLog).filter(TransferLog.player_uid == 2001).one()

        transfer_service.undo_operation(self.db, "HEIGO01", log.id, lambda *_args: None)

        self.assertIsNone(self.db.query(Player).filter(Player.uid == 2001).first())


if __name__ == "__main__":
    unittest.main()
