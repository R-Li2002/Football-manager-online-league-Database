from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Player, Team


SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "maintenance" / "rename_teams_from_workbook.py"
SPEC = importlib.util.spec_from_file_location("rename_teams_from_workbook", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


class RenameTeamsFromWorkbookTests(unittest.TestCase):
    def test_build_auto_mapping_uses_workbook_names(self):
        db_team_names = ["Bournemouth", "Manchester City", "Liverpool"]
        workbook_team_names = ["AFC Bournemouth", "Manchester City", "Liverpool"]

        mapping = MODULE.build_auto_mapping(db_team_names, workbook_team_names)

        self.assertEqual(mapping, {"Bournemouth": "AFC Bournemouth"})

    def test_build_auto_mapping_matches_normalized_existing_team_name(self):
        db_team_names = ["AS Roma"]
        workbook_team_names = ["Associazione Sportiva Roma"]

        mapping = MODULE.build_auto_mapping(db_team_names, workbook_team_names)

        self.assertEqual(mapping, {"AS Roma": "Associazione Sportiva Roma"})

    def test_apply_team_rename_updates_team_and_players(self):
        db = build_session()
        try:
            team = Team(name="Bournemouth", manager="Coach", level="超级")
            db.add(team)
            db.flush()
            db.add(
                Player(
                    uid=1,
                    name="P1",
                    age=20,
                    ca=120,
                    pa=150,
                    position="MC",
                    nationality="CN",
                    team_id=team.id,
                    team_name="Bournemouth",
                )
            )
            db.add(
                Player(
                    uid=2,
                    name="P2",
                    age=21,
                    ca=118,
                    pa=148,
                    position="ST",
                    nationality="CN",
                    team_id=None,
                    team_name="Bournemouth",
                )
            )
            db.commit()

            result = MODULE.apply_team_rename(db, "Bournemouth", "AFC Bournemouth")
            db.commit()

            renamed_team = db.query(Team).filter(Team.id == team.id).one()
            players = db.query(Player).order_by(Player.uid).all()

            self.assertEqual(result["updated_player_count"], 2)
            self.assertEqual(renamed_team.name, "AFC Bournemouth")
            self.assertEqual([player.team_name for player in players], ["AFC Bournemouth", "AFC Bournemouth"])
            self.assertEqual([player.team_id for player in players], [team.id, team.id])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
