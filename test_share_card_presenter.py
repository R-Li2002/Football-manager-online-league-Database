import unittest

from services.share_page_service import build_player_share_card_model, build_preview_player
from test_internal_share_page import _sample_player_detail


class ShareCardPresenterTests(unittest.TestCase):
    def test_preview_player_applies_growth_and_ca_gain(self):
        player = _sample_player_detail()

        preview = build_preview_player(player, 5)

        self.assertEqual(preview["preview_step"], 5)
        self.assertEqual(preview["preview_ca"], player.ca + 90)
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
        self.assertEqual(model.preview_label, "Growth Preview +2")
        self.assertEqual([group.title for group in model.attribute_groups], ["Technical", "Mental", "Physical", "Hidden"])
        self.assertEqual(len(model.radar_metrics), 8)
        self.assertTrue(any(chip.label == "AMC" for chip in model.position_chips))

    def test_card_model_builds_goalkeeper_technical_group(self):
        player = _sample_player_detail()
        player.pos_gk = 18
        player.reflexes = 16
        player.handling = 15
        player.one_on_ones = 14

        model = build_player_share_card_model(player, step=0)

        self.assertTrue(model.is_goalkeeper)
        technical_labels = [item.label for item in model.attribute_groups[0].items]
        self.assertIn("Reflexes", technical_labels)
        self.assertIn("Handling", technical_labels)
