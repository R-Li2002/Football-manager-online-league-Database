from types import SimpleNamespace

from services.read_presenters import (
    build_attribute_search_response,
    build_player_attribute_detail_response,
    build_player_reaction_leaderboard_item_response,
)


def _detail_attr(**overrides):
    base = {
        "uid": 1,
        "name": "Sample",
        "position": "ST",
        "age": 24,
        "ca": None,
        "pa": None,
        "nationality": "NO",
        "club": "City",
        "height": 194,
        "weight": 88,
        "left_foot": 10,
        "right_foot": 18,
        "radar_defense": 1.0,
        "radar_physical": 15.0,
        "radar_speed": 16.0,
        "radar_creativity": 12.0,
        "radar_attack": 18.0,
        "radar_technical": 14.0,
        "radar_aerial": 17.0,
        "radar_mental": 14.0,
        "birth_date": "",
        "national_caps": 0,
        "national_goals": 0,
        "player_habits": "",
        "player_habits_raw_code": "",
        "player_habits_high_bits": "",
        "corner": 0,
        "crossing": 0,
        "dribbling": 0,
        "finishing": 0,
        "first_touch": 0,
        "free_kick": 0,
        "heading": 0,
        "long_shots": 0,
        "long_throws": 0,
        "marking": 0,
        "passing": 0,
        "penalty": 0,
        "tackling": 0,
        "technique": 0,
        "aggression": 0,
        "anticipation": 0,
        "bravery": 0,
        "composure": 0,
        "concentration": 0,
        "decisions": 0,
        "determination": 0,
        "flair": 0,
        "leadership": 0,
        "off_the_ball": 0,
        "positioning": 0,
        "teamwork": 0,
        "vision": 0,
        "work_rate": 0,
        "acceleration": 0,
        "agility": 0,
        "balance": 0,
        "jumping": 0,
        "natural_fitness": 0,
        "pace": 0,
        "stamina": 0,
        "strength": 0,
        "consistency": 0,
        "dirtiness": 0,
        "important_matches": 0,
        "injury_proneness": 0,
        "versatility": 0,
        "adaptability": 0,
        "ambition": 0,
        "controversy": 0,
        "loyalty": 0,
        "pressure": 0,
        "professionalism": 0,
        "sportsmanship": 0,
        "temperament": 0,
        "aerial_ability": 0,
        "command_of_area": 0,
        "communication": 0,
        "eccentricity": 0,
        "handling": 0,
        "kicking": 0,
        "one_on_ones": 0,
        "reflexes": 0,
        "rushing_out": 0,
        "tendency_to_punch": 0,
        "throwing": 0,
        "pos_gk": 0,
        "pos_dl": 0,
        "pos_dc": 0,
        "pos_dr": 0,
        "pos_wbl": 0,
        "pos_wbr": 0,
        "pos_dm": 0,
        "pos_ml": 0,
        "pos_mc": 0,
        "pos_mr": 0,
        "pos_aml": 0,
        "pos_amc": 0,
        "pos_amr": 0,
        "pos_st": 20,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_attribute_search_presenter_coerces_null_ca_pa_to_zero():
    payload = build_attribute_search_response(
        SimpleNamespace(
            uid=9,
            name="Erling Haaland",
            data_version="2630",
            position="ST",
            age=24,
            ca=None,
            pa=None,
            nationality="NO",
            club="Man City",
        ),
        data_version="2630",
        heigo_club="Man City",
    )

    assert payload.ca == 0
    assert payload.pa == 0


def test_attribute_detail_presenter_coerces_null_ca_pa_to_zero():
    payload = build_player_attribute_detail_response(
        _detail_attr(),
        data_version="2630",
        heigo_club="Man City",
        reaction_summary={},
    )

    assert payload.ca == 0
    assert payload.pa == 0


def test_reaction_leaderboard_presenter_coerces_null_ca_pa_to_zero():
    payload = build_player_reaction_leaderboard_item_response(
        SimpleNamespace(
            uid=9,
            name="Erling Haaland",
            position="ST",
            age=24,
            ca=None,
            pa=None,
            heigo_club="Man City",
            flowers=1,
            eggs=0,
            net_score=1,
            total_reactions=1,
            updated_at=None,
        ),
        data_version="2630",
        fallback_team="大海",
    )

    assert payload.ca == 0
    assert payload.pa == 0
