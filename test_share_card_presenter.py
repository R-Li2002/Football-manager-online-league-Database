import unittest

from services.share_card_model_service import build_roster_share_card_model
from services.share_page_service import build_player_share_card_model, build_preview_player
from test_internal_share_page import _sample_player_detail
from test_internal_share_page import _sample_team_info, _sample_team_players


class ShareCardPresenterTests(unittest.TestCase):
    def test_preview_player_applies_growth_without_preview_ca(self):
        player = _sample_player_detail()

        preview = build_preview_player(player, 5)

        self.assertEqual(preview["preview_step"], 5)
        self.assertNotIn("preview_ca", preview)
        self.assertEqual(preview["passing"], min(20, player.passing + 5))

    def test_preview_player_applies_weak_foot_bonus_at_step_five(self):
        player = _sample_player_detail()

        preview = build_preview_player(player, 5)

        self.assertEqual(preview["left_foot"], player.left_foot + 1)
        self.assertEqual(preview["right_foot"], player.right_foot)

    def test_card_model_builds_outfield_groups_and_radar(self):
        model = build_player_share_card_model(_sample_player_detail(), version="2026-03", step=2)

        self.assertFalse(model.is_goalkeeper)
        self.assertEqual(model.version_label, "2026-03")
        self.assertEqual(model.preview_label, "成长预览 +2")
        self.assertEqual(model.reaction_flower_count, 0)
        self.assertEqual(model.reaction_egg_count, 0)
        self.assertEqual([group.title for group in model.attribute_groups], ["技术", "精神", "身体", "隐藏"])
        self.assertEqual(len(model.radar_metrics), 8)
        self.assertTrue(any(chip.label == "AMC" for chip in model.position_chips))
        self.assertTrue(any(marker.label == "AMC" for marker in model.position_markers))

    def test_card_model_builds_goalkeeper_technical_group(self):
        player = _sample_player_detail()
        player.pos_gk = 18
        player.reflexes = 16
        player.handling = 15
        player.one_on_ones = 14

        model = build_player_share_card_model(player, step=0)

        self.assertTrue(model.is_goalkeeper)
        technical_labels = [item.label for item in model.attribute_groups[0].items]
        self.assertIn("反应", technical_labels)
        self.assertIn("手控球", technical_labels)

    def test_roster_card_model_expands_canvas_for_twenty_players(self):
        players = _sample_team_players()
        while len(players) < 20:
            idx = len(players)
            players.append(
                players[0].model_copy(
                    update={
                        "uid": 24048100 + idx,
                        "name": f"Barcelona Player {idx + 1}",
                        "age": 20 + idx,
                        "ca": 140 + idx,
                        "pa": 155 + idx,
                        "wage": 0.5 + idx * 0.01,
                        "slot_type": "8M" if idx % 5 == 0 else "",
                    }
                )
            )

        model = build_roster_share_card_model("Barcelona", players, team_info=_sample_team_info(), page=1)

        self.assertEqual(len(model.player_rows), 20)
        self.assertGreaterEqual(model.canvas_height, 1330)
