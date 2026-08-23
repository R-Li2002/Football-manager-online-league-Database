import unittest
from datetime import datetime

from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import CandidateList, CandidateListPlayer, Player, PlayerAttributeVersion, Team
from services import candidate_list_service


class CandidateListExportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_export_prefers_league_roster_for_current_ca_pa_and_uses_database_for_initial_ca(self):
        league_team = Team(id=1, name="联赛球队", level="超级")
        candidate_list = CandidateList(
            id=1,
            name="测试候选名单",
            description="核对 CA 与 PA 来源",
            status="published",
            type="custom",
            base_data_version="26.3",
        )
        self.db.add_all([
            league_team,
            candidate_list,
            Player(uid=101, name="联赛球员", age=22, ca=132, pa=156, position="MC", nationality="China", team_id=1, team_name="联赛球队"),
            PlayerAttributeVersion(uid=101, data_version="26.3", name="联赛球员", age=22, ca=108, pa=148, position="MC", nationality="China", club="Reality FC"),
            PlayerAttributeVersion(uid=202, data_version="26.3", name="库内球员", age=24, ca=116, pa=142, position="DC", nationality="France", club="Database FC"),
            CandidateListPlayer(
                list_id=1,
                uid=101,
                data_version="26.3",
                name_snapshot="联赛球员",
                heigo_club_snapshot="联赛球队",
                ca_snapshot=108,
                pa_snapshot=148,
                added_at=datetime(2026, 8, 20, 10, 30),
            ),
            CandidateListPlayer(
                list_id=1,
                uid=202,
                data_version="26.3",
                name_snapshot="库内球员",
                heigo_club_snapshot="大海",
                ca_snapshot=116,
                pa_snapshot=142,
                added_at=datetime(2026, 8, 21, 11, 45),
            ),
        ])
        self.db.commit()

        output, filename = candidate_list_service.build_candidate_list_excel(self.db, 1, public=True)
        workbook = load_workbook(output, data_only=False)
        sheet = workbook["候选名单"]

        self.assertTrue(filename.startswith("HEIGO_candidate_list_1_"))
        self.assertEqual([cell.value for cell in sheet[5]][8:11], ["初始CA", "当前CA", "当前PA"])
        self.assertEqual(sheet["I6"].value, 108)
        self.assertEqual(sheet["J6"].value, 132)
        self.assertEqual(sheet["K6"].value, 156)
        self.assertEqual(sheet["L6"].value, "联赛名单")
        self.assertEqual(sheet["I7"].value, 116)
        self.assertEqual(sheet["J7"].value, 116)
        self.assertEqual(sheet["K7"].value, 142)
        self.assertEqual(sheet["L7"].value, "球员数据库")
        self.assertIn("当前CA、当前PA优先取联赛名单", sheet["A3"].value)
        self.assertEqual(sheet.freeze_panes, "A6")


if __name__ == "__main__":
    unittest.main()
