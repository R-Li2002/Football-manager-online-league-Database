import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Match, Player, Team
from schemas_write import SuspensionRecordUpdateRequest, TeamLineupUpdateRequest
from services import suspension_service, team_lineup_service


class TeamLineupServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.team = Team(name="Alpha", manager="Coach A", level="超级", wage=0, final_wage=0)
        self.other_team = Team(name="Beta", manager="Coach B", level="甲级", wage=0, final_wage=0)
        self.db.add_all([self.team, self.other_team])
        self.db.flush()
        self.player = Player(uid=101, name="Starter", team_id=self.team.id, team_name=self.team.name, position="ST", ca=150, pa=160, wage=0)
        self.other_player = Player(uid=202, name="Outsider", team_id=self.other_team.id, team_name=self.other_team.name, position="GK", ca=140, pa=150, wage=0)
        self.db.add_all([self.player, self.other_player])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_default_lineup_is_public_and_unsaved(self):
        payload = team_lineup_service.get_team_lineup(self.db, self.team.id)
        self.assertEqual(payload.formation, "4-3-3")
        self.assertEqual(payload.picks, {})
        self.assertFalse(payload.is_saved)
        self.assertFalse(payload.can_edit)

    @patch("services.team_lineup_service._resolve_editor", return_value=(True, "coach:alpha"))
    def test_coach_can_save_valid_team_lineup(self, _resolve_editor):
        extra_players = [
            Player(uid=uid, name=f"Starter {uid}", team_id=self.team.id, team_name=self.team.name, position="M C", ca=140, pa=160, wage=0)
            for uid in range(102, 112)
        ]
        self.db.add_all(extra_players)
        self.db.commit()
        slots = ["fw_l", "fw_c", "fw_r", "am_wl", "am_l", "am_c", "am_r", "am_wr", "mc_l", "dm_c", "gk"]
        request = TeamLineupUpdateRequest(
            formation="4-3-3",
            picks={slot: uid for slot, uid in zip(slots, range(101, 112))},
        )
        payload = team_lineup_service.save_team_lineup(self.db, self.team.id, request)
        self.assertTrue(payload.is_saved)
        self.assertEqual(len(payload.picks), 11)
        self.assertEqual(payload.picks["dm_c"], 110)
        self.assertEqual(payload.updated_by, "coach:alpha")

    @patch("services.team_lineup_service._resolve_editor", return_value=(True, "coach:alpha"))
    def test_lineup_requires_exactly_eleven_players(self, _resolve_editor):
        with self.assertRaises(HTTPException) as context:
            team_lineup_service.save_team_lineup(
                self.db,
                self.team.id,
                TeamLineupUpdateRequest(formation="4-3-3", picks={"fw_c": self.player.uid}),
            )
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("11", context.exception.detail)

    @patch("services.team_lineup_service._resolve_editor", return_value=(False, "coach:beta"))
    def test_other_coach_cannot_save_lineup(self, _resolve_editor):
        with self.assertRaises(HTTPException) as context:
            team_lineup_service.save_team_lineup(
                self.db,
                self.team.id,
                TeamLineupUpdateRequest(formation="4-3-3", picks={}),
            )
        self.assertEqual(context.exception.status_code, 403)

    @patch("services.team_lineup_service._resolve_editor", return_value=(True, "admin:root"))
    def test_lineup_rejects_player_from_another_team(self, _resolve_editor):
        with self.assertRaises(HTTPException) as context:
            team_lineup_service.save_team_lineup(
                self.db,
                self.team.id,
                TeamLineupUpdateRequest(formation="4-3-3", picks={"gk": self.other_player.uid}),
            )
        self.assertEqual(context.exception.status_code, 400)

    @patch("services.team_lineup_service._resolve_editor", return_value=(True, "coach:alpha"))
    def test_lineup_rejects_player_still_serving_a_suspension(self, _resolve_editor):
        extra_players = [
            Player(uid=uid, name=f"Starter {uid}", team_id=self.team.id, team_name=self.team.name, position="M C", ca=140, pa=160, wage=0)
            for uid in range(102, 112)
        ]
        self.db.add_all(extra_players)
        self.db.add(
            Match(
                level="超级",
                round_no=1,
                home_team_id=self.team.id,
                home_team_name=self.team.name,
                away_team_id=self.other_team.id,
                away_team_name=self.other_team.name,
                status="scheduled",
            )
        )
        self.db.commit()
        suspension_service.update_suspension_record(
            self.db,
            "editor",
            SuspensionRecordUpdateRequest(player_uid=self.player.uid, yellow_cards=3, suspension_matches=2),
            lambda *_args: None,
        )
        slots = ["fw_l", "fw_c", "fw_r", "am_wl", "am_l", "am_c", "am_r", "am_wr", "mc_l", "dm_c", "gk"]

        with self.assertRaises(HTTPException) as context:
            team_lineup_service.save_team_lineup(
                self.db,
                self.team.id,
                TeamLineupUpdateRequest(
                    formation="4-3-3",
                    picks={slot: uid for slot, uid in zip(slots, range(101, 112))},
                ),
            )

        self.assertIn("当前停赛球员", context.exception.detail)
        self.assertIn("Starter", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
