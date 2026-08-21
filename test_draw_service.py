import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from fastapi import HTTPException

from models import CandidateListPlayer, CupGroupTeam, DrawPoolEntry, DrawSession, OperationAudit, Player, Team
from schemas_write import DrawPoolEntryRequest, DrawSessionCreateRequest, DrawSessionUpdateRequest
from services import draw_service


class DrawServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _teams(self, count: int) -> list[Team]:
        rows = [Team(name=f"球队{index:02d}", manager=f"教练{index:02d}", level="超级") for index in range(1, count + 1)]
        self.db.add_all(rows)
        self.db.commit()
        return rows

    def test_group_draw_is_click_driven_and_balanced(self):
        teams = self._teams(30)
        entries = [
            DrawPoolEntryRequest(team_id=team.id, pot_no=(index // 5) + 1)
            for index, team in enumerate(teams)
        ]
        first = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="冠军杯抽签", draw_type="champions_group", random_seed="fixed-seed", entries=entries),
        )
        draw_service.lock_session(self.db, "admin", first.id)
        by_pot = {
            pot_no: [row for row in first.entries if row.pot_no == pot_no]
            for pot_no in range(1, 7)
        }
        for pot_no in range(1, 7):
            for entry in by_pot[pot_no]:
                first_result = draw_service.draw_next(self.db, "admin", first.id, entry.id)
        self.assertEqual(set(first_result.result["groups"]), {"A", "B", "C", "D", "E"})
        for group in first_result.result["groups"].values():
            self.assertEqual(len(group), 6)
            self.assertEqual({row["pot_no"] for row in group}, {1, 2, 3, 4, 5, 6})
        draw_service.write_to_cup(self.db, "admin", first.id)
        self.assertEqual(self.db.query(CupGroupTeam).filter(CupGroupTeam.competition == "champions_cup").count(), 30)
        self.assertGreater(len(draw_service.export_excel(self.db, first.id)), 1000)
        self.assertTrue(draw_service.export_png(self.db, first.id).startswith(b"\x89PNG"))

    def test_group_draw_commits_exactly_the_clicked_team_per_step(self):
        teams = self._teams(30)
        entries = [
            DrawPoolEntryRequest(team_id=team.id, pot_no=(index // 5) + 1)
            for index, team in enumerate(teams)
        ]
        progressive = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="逐签冠军杯", draw_type="champions_group", random_seed="step-seed", entries=entries),
        )
        draw_service.lock_session(self.db, "admin", progressive.id)
        clicked_order = []
        for pot_no in range(1, 7):
            clicked_order.extend(sorted((row for row in progressive.entries if row.pot_no == pot_no), key=lambda row: row.team_id, reverse=True))
        first_pick = draw_service.draw_next(self.db, "admin", progressive.id, clicked_order[0].id)
        self.assertEqual(first_pick.status, "drawing")
        self.assertEqual(len(first_pick.picks), 1)
        self.assertEqual(first_pick.picks[0].entry.id, clicked_order[0].id)
        self.assertEqual(first_pick.picks[0].target_group, "A")
        self.assertEqual(first_pick.picks[0].target_slot, 1)
        for expected_count, entry in enumerate(clicked_order[1:], start=2):
            progressive_result = draw_service.draw_next(self.db, "admin", progressive.id, entry.id)
            self.assertEqual(len(progressive_result.picks), expected_count)
        self.assertEqual(progressive_result.status, "completed")
        self.assertTrue(all(pick.random_value.startswith("click:") for pick in progressive_result.picks))

    def test_seeded_pair_draw_reveals_first_side_then_opponent(self):
        teams = self._teams(16)
        entries = [
            DrawPoolEntryRequest(team_id=team.id, seed_status="seeded" if index < 8 else "unseeded")
            for index, team in enumerate(teams)
        ]
        session = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="逐签16强", draw_type="champions_r16", random_seed="pair-step-seed", entries=entries),
        )
        draw_service.lock_session(self.db, "admin", session.id)
        seeded_entries = [row for row in session.entries if row.seed_status == "seeded"]
        unseeded_entries = [row for row in session.entries if row.seed_status == "unseeded"]
        with self.assertRaises(HTTPException) as wrong_side:
            draw_service.draw_next(self.db, "admin", session.id, unseeded_entries[0].id)
        self.assertEqual(wrong_side.exception.status_code, 409)
        first_side = draw_service.draw_next(self.db, "admin", session.id, seeded_entries[-1].id)
        self.assertEqual(first_side.status, "drawing")
        self.assertEqual(len(first_side.picks), 0)
        self.assertEqual(first_side.result["pending_pair"]["side"], "seeded")
        first_entry_id = first_side.result["pending_pair"]["entry_id"]

        first_pair = draw_service.draw_next(self.db, "admin", session.id, unseeded_entries[-1].id)
        self.assertEqual(len(first_pair.picks), 1)
        self.assertNotIn("pending_pair", first_pair.result)
        self.assertEqual(first_pair.picks[0].entry.id, first_entry_id)
        self.assertEqual(first_pair.picks[0].entry.seed_status, "seeded")
        self.assertEqual(first_pair.picks[0].paired_entry.seed_status, "unseeded")
        for index in range(7):
            draw_service.draw_next(self.db, "admin", session.id, seeded_entries[index].id)
            result = draw_service.draw_next(self.db, "admin", session.id, unseeded_entries[index].id)
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.picks), 8)

    def test_lottery_uses_weights_and_never_selects_same_team_twice(self):
        teams = self._teams(3)
        players = []
        for team_index, team in enumerate(teams):
            for player_index in range(2):
                players.append(Player(
                    uid=1000 + team_index * 10 + player_index,
                    name=f"球员{team_index}-{player_index}",
                    age=25,
                    initial_ca=165,
                    ca=165,
                    pa=165,
                    position="MC",
                    team_id=team.id,
                    team_name=team.name,
                ))
        self.db.add_all(players)
        self.db.commit()
        entries = [DrawPoolEntryRequest(player_uid=player.uid, self_save_count=2 if player.uid == 1000 else 0) for player in players]
        session = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="乐透", draw_type="lottery", random_seed="lottery-seed", config={"limit": 3}, entries=entries),
        )
        locked = draw_service.lock_session(self.db, "admin", session.id)
        weighted = next(row for row in locked.entries if row.player_uid == 1000)
        self.assertEqual(weighted.weight, 4)

        result = locked
        selected_team_ids = set()
        for _ in range(3):
            selected = next(row for row in result.entries if row.is_active and row.team_id not in selected_team_ids)
            selected_team_ids.add(selected.team_id)
            result = draw_service.draw_next_lottery(self.db, "admin", session.id, selected.id)
        active = [pick for pick in result.picks if pick.status == "active"]
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(active), 3)
        self.assertEqual(len({pick.entry.team_id for pick in active}), 3)
        linked = draw_service.create_lottery_candidate_list(self.db, "admin", session.id)
        self.assertIsNotNone(linked.candidate_list_id)
        self.assertEqual(self.db.query(CandidateListPlayer).filter(CandidateListPlayer.list_id == linked.candidate_list_id).count(), 3)

    def test_custom_team_draw_supports_balanced_groups_and_odd_pairs(self):
        teams = self._teams(6)
        entries = [DrawPoolEntryRequest(team_id=team.id) for team in teams]
        entries.append(DrawPoolEntryRequest(entity_name="临时全明星队"))
        grouped = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="自由球队分组", draw_type="custom_team", random_seed="custom-groups", config={"mode": "groups", "group_count": 3}, entries=entries),
        )
        draw_service.lock_session(self.db, "admin", grouped.id)
        grouped_result = None
        for entry in grouped.entries:
            grouped_result = draw_service.draw_next(self.db, "admin", grouped.id, entry.id)

        self.assertEqual(set(grouped_result.result["groups"]), {"A", "B", "C"})
        self.assertEqual(sorted(len(rows) for rows in grouped_result.result["groups"].values()), [2, 2, 3])
        self.assertEqual(len(grouped_result.picks), 7)

        paired = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="自由球队配对", draw_type="custom_team", random_seed="custom-pairs", config={"mode": "pairs"}, entries=entries),
        )
        draw_service.lock_session(self.db, "admin", paired.id)
        paired_result = None
        for entry in paired.entries:
            paired_result = draw_service.draw_next(self.db, "admin", paired.id, entry.id)

        self.assertEqual(len(paired_result.picks), 4)
        self.assertEqual(sum(pick.paired_entry is None for pick in paired_result.picks), 1)

        progressive = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="逐签自由配对", draw_type="custom_team", random_seed="custom-pairs", config={"mode": "pairs"}, entries=entries),
        )
        draw_service.lock_session(self.db, "admin", progressive.id)
        first_side = draw_service.draw_next(self.db, "admin", progressive.id, progressive.entries[-1].id)
        self.assertEqual(len(first_side.picks), 0)
        self.assertIn("pending_pair", first_side.result)
        for entry in progressive.entries[:-1]:
            progressive_result = draw_service.draw_next(self.db, "admin", progressive.id, entry.id)
        self.assertEqual(progressive_result.status, "completed")
        self.assertEqual(len(progressive_result.picks), 4)
        self.assertEqual(sum(pick.paired_entry is None for pick in progressive_result.picks), 1)

    def test_custom_player_draw_supports_database_and_manual_list_entries(self):
        team = self._teams(1)[0]
        players = [
            Player(uid=2101, name="自由球员甲", team_id=team.id, team_name=team.name),
            Player(uid=2102, name="自由球员乙", team_id=team.id, team_name=team.name),
        ]
        self.db.add_all(players)
        self.db.commit()
        session = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(
                name="自由球员名单",
                draw_type="custom_player",
                random_seed="custom-player-list",
                config={"mode": "list", "result_count": 2},
                entries=[
                    DrawPoolEntryRequest(player_uid=2101),
                    DrawPoolEntryRequest(player_uid=2102),
                    DrawPoolEntryRequest(entity_name="临时嘉宾", team_name="嘉宾队"),
                ],
            ),
        )
        draw_service.lock_session(self.db, "admin", session.id)
        result = draw_service.draw_next(self.db, "admin", session.id, session.entries[1].id)
        result = draw_service.draw_next(self.db, "admin", session.id, session.entries[0].id)

        self.assertEqual(result.result["mode"], "list")
        self.assertEqual(result.result["selected_count"], 2)
        self.assertEqual(len(result.picks), 2)
        self.assertIn("自由球员名单", draw_service.export_text(self.db, session.id))

    def test_full_execute_is_rejected_because_click_must_choose_each_result(self):
        team = self._teams(1)[0]
        session = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="禁止预生成", draw_type="custom_team", config={"mode": "list"}, entries=[DrawPoolEntryRequest(team_id=team.id)]),
        )
        draw_service.lock_session(self.db, "admin", session.id)
        with self.assertRaises(HTTPException) as context:
            draw_service.execute_draw(self.db, "admin", session.id)
        self.assertEqual(context.exception.status_code, 409)

    def test_empty_draft_can_be_edited_incrementally_and_deleted(self):
        team = self._teams(1)[0]
        session = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="空白草稿", draw_type="custom_team", random_seed="draft-seed", entries=[]),
        )
        self.assertEqual(session.entry_count, 0)

        updated = draw_service.update_session(
            self.db,
            "editor",
            session.id,
            DrawSessionUpdateRequest(
                name="边编辑边抽签",
                season_label="第52届",
                random_seed="edited-seed",
                config={"mode": "groups", "group_count": 2},
                entries=[DrawPoolEntryRequest(team_id=team.id)],
            ),
        )
        self.assertEqual(updated.name, "边编辑边抽签")
        self.assertEqual(updated.season_label, "第52届")
        self.assertEqual(updated.random_seed, "edited-seed")
        self.assertEqual(updated.entry_count, 1)

        result = draw_service.delete_session(self.db, "editor", session.id)
        self.assertTrue(result["success"])
        self.assertEqual(self.db.query(DrawSession).filter(DrawSession.id == session.id).count(), 0)
        self.assertEqual(self.db.query(DrawPoolEntry).filter(DrawPoolEntry.session_id == session.id).count(), 0)
        audit = self.db.query(OperationAudit).filter(OperationAudit.category == "draw", OperationAudit.action == "delete").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details.get("draw_session_id"), session.id)

    def test_only_draft_or_void_draws_can_be_deleted(self):
        team = self._teams(1)[0]
        locked = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(
                name="已锁池任务",
                draw_type="custom_team",
                random_seed="locked-seed",
                config={"mode": "list"},
                entries=[DrawPoolEntryRequest(team_id=team.id)],
            ),
        )
        draw_service.lock_session(self.db, "admin", locked.id)
        with self.assertRaises(HTTPException) as context:
            draw_service.delete_session(self.db, "admin", locked.id)
        self.assertEqual(context.exception.status_code, 409)

        voided = draw_service.create_session(
            self.db,
            "admin",
            DrawSessionCreateRequest(name="已作废任务", draw_type="custom_team", entries=[]),
        )
        draw_service.void_session(self.db, "admin", voided.id, "测试清理")
        result = draw_service.delete_session(self.db, "admin", voided.id)
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
