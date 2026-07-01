import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Player, Team
from schemas_write import SuspensionRecordUpdateRequest
from services import suspension_service


class SuspensionServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        self.team = Team(name="Alpha", level="超级", manager="Alpha Boss")
        self.hidden_team = Team(name="Hidden", level="隐藏", manager="Hidden Boss")
        self.db.add_all([self.team, self.hidden_team])
        self.db.commit()
        self.players = [
            Player(uid=101, name="Alpha One", team_id=self.team.id, team_name=self.team.name),
            Player(uid=102, name="Alpha Two", team_id=self.team.id, team_name=self.team.name),
            Player(uid=103, name="Alpha Three", team_id=self.team.id, team_name=self.team.name),
            Player(uid=201, name="Hidden One", team_id=self.hidden_team.id, team_name=self.hidden_team.name),
        ]
        self.db.add_all(self.players)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _save(self, uid, **payload):
        request = SuspensionRecordUpdateRequest(player_uid=uid, **payload)
        return suspension_service.update_suspension_record(self.db, "editor", request, lambda *_args: None)

    def test_suspensions_are_grouped_by_status(self):
        self._save(101, yellow_cards=1, notes="一黄备注")
        self._save(102, yellow_cards=2)
        self._save(103, yellow_cards=3, red_card_suspended=True, red_injury_suspended=True, notes="停赛备注")

        response = suspension_service.get_suspensions(self.db)
        alpha = next(team for team in response.teams if team.team_name == "Alpha")

        self.assertEqual([item.player_uid for item in alpha.one_yellow], [101])
        self.assertEqual([item.player_uid for item in alpha.two_yellows], [102])
        self.assertEqual([item.player_uid for item in alpha.suspended], [103])
        self.assertIn("Alpha Three: 停赛备注", alpha.notes)

    def test_empty_payload_clears_existing_record(self):
        self._save(101, yellow_cards=2)
        self._save(101, yellow_cards=0, red_card_suspended=False, red_injury_suspended=False, notes="")

        response = suspension_service.get_suspensions(self.db)
        alpha = next(team for team in response.teams if team.team_name == "Alpha")
        self.assertEqual(alpha.one_yellow, [])
        self.assertEqual(alpha.two_yellows, [])
        self.assertEqual(alpha.suspended, [])

    def test_hidden_team_player_is_rejected(self):
        with self.assertRaises(HTTPException):
            self._save(201, yellow_cards=1)


if __name__ == "__main__":
    unittest.main()
