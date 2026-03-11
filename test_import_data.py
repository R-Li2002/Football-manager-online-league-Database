import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, init_database
from import_data import (
    DEFAULT_LEAGUE_INFO_VALUES,
    HIDDEN_SEA_TEAM_LEVEL,
    HIDDEN_SEA_TEAM_NAME,
    run_import,
)
from models import LeagueInfo, Player, PlayerAttribute, Team


TEAM_HEADER_ROW = [
    None,
    None,
    None,
    "球队名",
    "主教",
    "级别",
    "额外工资",
    "税后",
    "备注",
]


DEFAULT_TEAM_ROWS = [
    {"info_key": "届数", "info_value": 85, "name": "Alpha FC", "manager": "Coach A", "level": "超级", "extra_wage": 0.2, "after_tax": 0, "notes": ""},
    {"info_key": "成长年龄上限", "info_value": 24, "name": "Beta FC", "manager": "Coach B", "level": "甲级", "extra_wage": 0.0, "after_tax": 0, "notes": "+0.1M"},
]

DEFAULT_PLAYER_ROWS = [
    {"uid": 1, "name": "张三", "age": 20, "initial_ca": 120, "ca": 125, "pa": 150, "position": "MC", "nationality": "CN", "club_name": "Alpha FC"},
    {"uid": 2, "name": "李四", "age": 21, "initial_ca": 118, "ca": 121, "pa": 148, "position": "GK", "nationality": "CN", "club_name": "Beta FC"},
]


def default_mapping_rows(player_rows):
    return [
        {
            "uid": player["uid"],
            "name": player["name"],
            "age": player["age"],
            "ca": player["ca"],
            "pa": player["pa"],
            "nationality": player["nationality"],
            "team_name": player.get("league_team_name", player["club_name"]),
            "position": player["position"],
        }
        for player in player_rows
    ]


def write_workbook(
    path: Path,
    *,
    include_position_column: bool = True,
    team_rows=None,
    player_rows=None,
    mapping_rows=None,
) -> None:
    team_rows = team_rows or DEFAULT_TEAM_ROWS
    player_rows = player_rows or DEFAULT_PLAYER_ROWS
    mapping_rows = mapping_rows or default_mapping_rows(player_rows)

    workbook = Workbook()
    overview = workbook.active
    overview.title = "信息总览"

    overview.append(["说明：测试导入", None, None, None, None, None, None, None, None])
    overview.append(TEAM_HEADER_ROW)
    for team in team_rows:
        overview.append(
            [
                team["info_key"],
                team["info_value"],
                None,
                team["name"],
                team["manager"],
                team["level"],
                team["extra_wage"],
                team["after_tax"],
                team["notes"],
            ]
        )
    overview.append(["8M名额", 1.5])
    overview.append(["7M名额", 1.3])
    overview.append(["可成长名额", 1.1])
    overview.append(["非名PA6M", 0.9])
    overview.append(["非名身价1M", 1.0])
    overview.append(["非名其他", 0.7])
    overview.append(["注：名额GK系数为 1"])

    players_sheet = workbook.create_sheet("联赛名单")
    player_headers = [
        "编\u200b号",
        "姓\u200b名",
        "年\u200b龄",
        "初始CA",
        "当前CA",
        "PA",
        "位\u200b置",
        "国籍",
        "俱乐部",
    ]
    include_league_team_column = any("league_team_name" in player for player in player_rows)
    if include_league_team_column:
        player_headers.append("联赛球队")
    if not include_position_column:
        player_headers.remove("位\u200b置")
    players_sheet.append(player_headers)
    for player in player_rows:
        row = [
            player["uid"],
            player["name"],
            player["age"],
            player["initial_ca"],
            player["ca"],
            player["pa"],
            player["position"],
            player["nationality"],
            player["club_name"],
        ]
        if include_league_team_column:
            row.append(player.get("league_team_name", ""))
        if include_position_column:
            players_sheet.append(row)
        else:
            if include_league_team_column:
                players_sheet.append([row[0], row[1], row[2], row[3], row[4], row[5], row[7], row[8], row[9]])
            else:
                players_sheet.append([row[0], row[1], row[2], row[3], row[4], row[5], row[7], row[8]])

    mapping_sheet = workbook.create_sheet("球员对应球队")
    mapping_sheet.append(["UID", "球员名", "年龄", "CA", "PA", "国籍", "球队", "位置", "联赛名单有无"])
    for player in mapping_rows:
        mapping_sheet.append(
            [
                player["uid"],
                player["name"],
                player["age"],
                player["ca"],
                player["pa"],
                player["nationality"],
                player["team_name"],
                player["position"],
                "",
            ]
        )

    workbook.save(path)


def write_attributes_csv(path: Path) -> None:
    df = pd.DataFrame(
        [
            {"UID": 1, "姓名": "张三", "位置": "MC", "年龄": 20, "ca": 125, "pa": 150, "国籍": "CN", "俱乐部": "Alpha FC", "角球": 12},
            {"UID": 2, "姓名": "李四", "位置": "GK", "年龄": 21, "ca": 121, "pa": 148, "国籍": "CN", "俱乐部": "Beta FC", "角球": 5},
        ]
    )
    df.to_csv(path, index=False, encoding="utf-8-sig")


class ImportDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root_dir = Path(self.temp_dir.name)
        self.workbook_path = self.root_dir / "fixture.xlsx"
        self.attributes_csv_path = self.root_dir / "fixture.csv"
        write_workbook(self.workbook_path)
        write_attributes_csv(self.attributes_csv_path)

        self.db_path = self.root_dir / "import_test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(bind=self.engine)
        init_database(target_engine=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def count_rows(self) -> dict[str, int]:
        session = self.SessionLocal()
        try:
            return {
                "league_info": session.query(LeagueInfo).count(),
                "teams": session.query(Team).count(),
                "players": session.query(Player).count(),
                "player_attributes": session.query(PlayerAttribute).count(),
            }
        finally:
            session.close()

    def test_dry_run_validates_without_committing(self):
        report = run_import(
            workbook_path=self.workbook_path.name,
            attributes_csv_path=self.attributes_csv_path.name,
            root_dir=self.root_dir,
            target_engine=self.engine,
            dry_run=True,
        )

        self.assertFalse(report.has_errors)
        self.assertFalse(report.committed)
        self.assertEqual(report.datasets["league_info"].created, len(DEFAULT_LEAGUE_INFO_VALUES))
        self.assertEqual(report.datasets["teams"].created, 3)
        self.assertEqual(report.datasets["players"].created, 2)
        self.assertEqual(report.datasets["player_attributes"].created, 2)
        self.assertEqual(report.datasets["team_cache_rebuild"].updated, 2)
        self.assertEqual(
            self.count_rows(),
            {"league_info": 0, "teams": 0, "players": 0, "player_attributes": 0},
        )

    def test_real_import_is_idempotent(self):
        first_report = run_import(
            workbook_path=self.workbook_path,
            attributes_csv_path=self.attributes_csv_path,
            target_engine=self.engine,
        )

        self.assertFalse(first_report.has_errors)
        self.assertTrue(first_report.committed)
        self.assertEqual(
            self.count_rows(),
            {
                "league_info": len(DEFAULT_LEAGUE_INFO_VALUES),
                "teams": 3,
                "players": 2,
                "player_attributes": 2,
            },
        )

        session = self.SessionLocal()
        try:
            visible_teams = session.query(Team).filter(Team.level != HIDDEN_SEA_TEAM_LEVEL).all()
            self.assertEqual(len(visible_teams), 2)
            self.assertTrue(all(team.stats_cache_refresh_mode == "full_recalc" for team in visible_teams))
            self.assertTrue(all(team.stats_cache_refresh_scopes == "roster,wage" for team in visible_teams))

            hidden_team = session.query(Team).filter(Team.name == HIDDEN_SEA_TEAM_NAME).one()
            self.assertEqual(hidden_team.level, HIDDEN_SEA_TEAM_LEVEL)
        finally:
            session.close()

        second_report = run_import(
            workbook_path=self.workbook_path,
            attributes_csv_path=self.attributes_csv_path,
            target_engine=self.engine,
        )

        self.assertFalse(second_report.has_errors)
        self.assertTrue(second_report.committed)
        self.assertEqual(second_report.datasets["league_info"].created, 0)
        self.assertEqual(second_report.datasets["league_info"].unchanged, len(DEFAULT_LEAGUE_INFO_VALUES))
        self.assertEqual(second_report.datasets["teams"].created, 0)
        self.assertEqual(second_report.datasets["teams"].updated, 0)
        self.assertEqual(second_report.datasets["teams"].unchanged, 3)
        self.assertEqual(second_report.datasets["players"].created, 0)
        self.assertEqual(second_report.datasets["players"].updated, 0)
        self.assertEqual(second_report.datasets["players"].unchanged, 2)
        self.assertEqual(second_report.datasets["player_attributes"].created, 0)
        self.assertEqual(second_report.datasets["player_attributes"].updated, 0)
        self.assertEqual(second_report.datasets["player_attributes"].unchanged, 2)
        self.assertEqual(
            self.count_rows(),
            {
                "league_info": len(DEFAULT_LEAGUE_INFO_VALUES),
                "teams": 3,
                "players": 2,
                "player_attributes": 2,
            },
        )

    def test_validation_errors_rollback_all_changes(self):
        bad_workbook_path = self.root_dir / "bad_fixture.xlsx"
        write_workbook(bad_workbook_path, include_position_column=False)

        report = run_import(
            workbook_path=bad_workbook_path,
            attributes_csv_path=self.attributes_csv_path,
            target_engine=self.engine,
        )

        self.assertTrue(report.has_errors)
        self.assertFalse(report.committed)
        self.assertTrue(report.datasets["players"].errors)
        self.assertIn("缺少列", report.datasets["players"].errors[0])
        self.assertEqual(
            self.count_rows(),
            {"league_info": 0, "teams": 0, "players": 0, "player_attributes": 0},
        )

    def test_mapping_sheet_backfills_position_and_normalizes_team_aliases(self):
        fallback_workbook_path = self.root_dir / "mapping_fallback.xlsx"
        write_workbook(
            fallback_workbook_path,
            team_rows=[
                {"info_key": "届数", "info_value": 85, "name": "Bournemouth", "manager": "Coach A", "level": "超级", "extra_wage": 0.0, "after_tax": 0, "notes": ""},
                {"info_key": "成长年龄上限", "info_value": 24, "name": "As Roma", "manager": "Coach B", "level": "甲级", "extra_wage": 0.0, "after_tax": 0, "notes": ""},
            ],
            player_rows=[
                {"uid": 10, "name": "王五", "age": 20, "initial_ca": 120, "ca": 123, "pa": 150, "position": "", "nationality": "CN", "club_name": "Bournemouth", "team_name": "AFC Bournemouth"},
                {"uid": 11, "name": "赵六", "age": 21, "initial_ca": 118, "ca": 121, "pa": 148, "position": "", "nationality": "CN", "club_name": "Associazione Sportiva Roma"},
            ],
            mapping_rows=[
                {"uid": 10, "name": "王五", "age": 20, "ca": 123, "pa": 150, "nationality": "CN", "team_name": "AFC Bournemouth", "position": "MC"},
                {"uid": 11, "name": "赵六", "age": 21, "ca": 121, "pa": 148, "nationality": "CN", "team_name": "Associazione Sportiva Roma", "position": "GK"},
            ],
        )

        report = run_import(
            workbook_path=fallback_workbook_path,
            attributes_csv_path=self.attributes_csv_path,
            target_engine=self.engine,
            strict_mode=False,
        )

        self.assertFalse(report.has_errors)
        self.assertTrue(report.committed)
        self.assertEqual(report.datasets["players"].details["player_team_overrides"], 2)
        self.assertEqual(report.datasets["players"].details["team_alias_hits"], 2)

        session = self.SessionLocal()
        try:
            players = session.query(Player).order_by(Player.uid).all()
            self.assertEqual([player.team_name for player in players], ["Bournemouth", "As Roma"])
            self.assertTrue(all(player.team_id for player in players))
            self.assertEqual([player.position for player in players], ["MC", "GK"])
        finally:
            session.close()

    def test_falls_back_to_club_when_explicit_league_team_is_not_in_league(self):
        fallback_workbook_path = self.root_dir / "club_fallback.xlsx"
        write_workbook(
            fallback_workbook_path,
            team_rows=[
                {"info_key": "届数", "info_value": 85, "name": "Eintracht Frankfurt", "manager": "Coach A", "level": "超级", "extra_wage": 0.0, "after_tax": 0, "notes": ""},
                {"info_key": "成长年龄上限", "info_value": 24, "name": "Beta FC", "manager": "Coach B", "level": "甲级", "extra_wage": 0.0, "after_tax": 0, "notes": ""},
            ],
            player_rows=[
                {"uid": 21, "name": "阿德莫拉", "age": 27, "initial_ca": 160, "ca": 160, "pa": 164, "position": "ST", "nationality": "NG", "club_name": "Eintracht Frankfurt", "league_team_name": "Fenerbahçe"},
            ],
            mapping_rows=[],
        )

        report = run_import(
            workbook_path=fallback_workbook_path,
            attributes_csv_path=self.attributes_csv_path,
            target_engine=self.engine,
            strict_mode=False,
        )

        self.assertFalse(report.has_errors)
        self.assertTrue(report.committed)
        self.assertEqual(report.datasets["players"].details["club_team_fallback_hits"], 1)

        session = self.SessionLocal()
        try:
            player = session.query(Player).filter(Player.uid == 21).one()
            self.assertEqual(player.team_name, "Eintracht Frankfurt")
            self.assertIsNotNone(player.team_id)
        finally:
            session.close()

    def test_strict_mode_reports_missing_position_and_team_mismatch_clearly(self):
        strict_workbook_path = self.root_dir / "strict_failure.xlsx"
        write_workbook(
            strict_workbook_path,
            team_rows=[
                {"info_key": "届数", "info_value": 85, "name": "Bournemouth", "manager": "Coach A", "level": "超级", "extra_wage": 0.0, "after_tax": 0, "notes": ""},
                {"info_key": "成长年龄上限", "info_value": 24, "name": "As Roma", "manager": "Coach B", "level": "甲级", "extra_wage": 0.0, "after_tax": 0, "notes": ""},
            ],
            player_rows=[
                {"uid": 31, "name": "王五", "age": 20, "initial_ca": 120, "ca": 123, "pa": 150, "position": "", "nationality": "CN", "club_name": "Bournemouth", "team_name": "AFC Bournemouth"},
                {"uid": 32, "name": "赵六", "age": 21, "initial_ca": 118, "ca": 121, "pa": 148, "position": "GK", "nationality": "CN", "club_name": "Associazione Sportiva Roma"},
            ],
            mapping_rows=[
                {"uid": 31, "name": "王五", "age": 20, "ca": 123, "pa": 150, "nationality": "CN", "team_name": "Bournemouth", "position": "MC"},
                {"uid": 32, "name": "赵六", "age": 21, "ca": 121, "pa": 148, "nationality": "CN", "team_name": "As Roma", "position": "GK"},
            ],
        )

        report = run_import(
            workbook_path=strict_workbook_path,
            attributes_csv_path=self.attributes_csv_path,
            target_engine=self.engine,
        )

        self.assertTrue(report.has_errors)
        self.assertFalse(report.committed)
        self.assertTrue(report.strict_mode)
        self.assertEqual(report.datasets["players"].details["error_counts"]["missing_position"], 1)
        self.assertEqual(report.datasets["players"].details["error_counts"]["team_name_mismatch"], 1)
        self.assertEqual(
            report.datasets["players"].details["strict_mode_guidance"],
            {
                "position_rule": "联赛名单.位置 必须非空",
                "team_rule": "联赛名单中的球队名必须与 信息总览.球队名 完全一致",
            },
        )
        mismatch_sample = report.datasets["players"].details["error_samples"]["team_name_mismatch"][0]
        self.assertEqual(mismatch_sample["provided_team_name"], "Associazione Sportiva Roma")
        self.assertEqual(mismatch_sample["club_team_name"], "Associazione Sportiva Roma")
        self.assertEqual(
            self.count_rows(),
            {"league_info": 0, "teams": 0, "players": 0, "player_attributes": 0},
        )

    def test_real_import_removes_stale_orphan_visible_teams(self):
        session = self.SessionLocal()
        try:
            session.add(Team(name="Legacy Roma", manager="Old", level="鐢茬骇", wage=0))
            session.commit()
        finally:
            session.close()

        report = run_import(
            workbook_path=self.workbook_path,
            attributes_csv_path=self.attributes_csv_path,
            target_engine=self.engine,
        )

        self.assertFalse(report.has_errors)
        self.assertTrue(report.committed)
        self.assertEqual(report.datasets["team_cleanup"].details["removed_count"], 1)
        self.assertEqual(report.datasets["team_cleanup"].details["removed_teams"], ["Legacy Roma"])

        session = self.SessionLocal()
        try:
            self.assertIsNone(session.query(Team).filter(Team.name == "Legacy Roma").first())
            self.assertEqual(session.query(Team).count(), 3)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
