import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.frontend_routes import build_frontend_router
from schemas_read import PlayerAttributeDetailResponse, PlayerResponse, TeamInfoResponse, WageDetailResponse


def _dummy_db():
    yield None


def _sample_player_detail() -> PlayerAttributeDetailResponse:
    return PlayerAttributeDetailResponse(
        uid=24048100,
        name="Dani Olmo",
        data_version="2026-03",
        position="M/AM C",
        age=27,
        ca=165,
        pa=170,
        nationality="Spain",
        club="Barcelona",
        heigo_club="Barcelona",
        height=179,
        weight=72,
        left_foot=14,
        right_foot=18,
        radar_defense=12,
        radar_physical=13,
        radar_speed=14,
        radar_creativity=16,
        radar_attack=15,
        radar_technical=16,
        radar_aerial=10,
        radar_mental=15,
        birth_date="1998-05-07",
        national_caps=0,
        national_goals=0,
        player_habits="Drops deep to receive the ball",
        player_habits_raw_code=None,
        player_habits_high_bits=None,
        corner=12,
        crossing=13,
        dribbling=16,
        finishing=14,
        first_touch=16,
        free_kick=14,
        heading=9,
        long_shots=15,
        long_throws=4,
        marking=7,
        passing=16,
        penalty=11,
        tackling=8,
        technique=17,
        aggression=10,
        anticipation=15,
        bravery=11,
        composure=16,
        concentration=14,
        decisions=15,
        determination=15,
        flair=17,
        leadership=9,
        off_the_ball=15,
        positioning=10,
        teamwork=14,
        vision=17,
        work_rate=13,
        acceleration=15,
        agility=16,
        balance=15,
        jumping=8,
        natural_fitness=14,
        pace=14,
        stamina=13,
        strength=10,
        consistency=13,
        dirtiness=4,
        important_matches=14,
        injury_proneness=8,
        versatility=15,
        adaptability=13,
        ambition=14,
        controversy=6,
        loyalty=11,
        pressure=15,
        professionalism=15,
        sportsmanship=13,
        temperament=14,
        aerial_ability=1,
        command_of_area=1,
        communication=1,
        eccentricity=1,
        handling=1,
        kicking=1,
        one_on_ones=1,
        reflexes=1,
        rushing_out=1,
        tendency_to_punch=1,
        throwing=1,
        pos_gk=1,
        pos_dl=1,
        pos_dc=1,
        pos_dr=1,
        pos_wbl=1,
        pos_wbr=1,
        pos_dm=12,
        pos_ml=1,
        pos_mc=17,
        pos_mr=1,
        pos_aml=8,
        pos_amc=18,
        pos_amr=1,
        pos_st=6,
        top_positions=[],
        radar_profile=[],
    )


def _sample_wage_detail() -> WageDetailResponse:
    return WageDetailResponse(
        initial_value=7.0,
        current_value=7.0,
        potential_value=7.0,
        final_value=7.0,
        initial_field=7.0,
        slot_type="7M",
        coefficient=0.13,
        wage=0.91,
    )


def _sample_team_players() -> list[PlayerResponse]:
    return [
        PlayerResponse(
            uid=24048100 + idx,
            name=f"Barcelona Player {idx + 1}",
            age=20 + idx,
            initial_ca=120 + idx,
            ca=140 + idx,
            pa=155 + idx,
            position="MC" if idx % 3 else "GK",
            nationality="Spain",
            team_name="Barcelona",
            wage=0.5 + idx * 0.01,
            slot_type="8M" if idx == 0 else "",
        )
        for idx in range(6)
    ]


def _sample_team_info() -> TeamInfoResponse:
    return TeamInfoResponse(id=1, name="Barcelona", manager="Xavi", level="Super", wage=8.4, notes=None)


class InternalSharePageTests(unittest.TestCase):
    def test_internal_share_page_renders_html(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=_sample_player_detail()):
            response = client.get(
                "/internal/share/player/24048100?version=2026-03&step=2",
                headers={"X-Internal-Share-Token": "share-secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("HEIGO PLAYER SHARE", response.text)
        self.assertIn("Dani Olmo", response.text)
        self.assertIn("Growth Preview +2", response.text)
        self.assertIn("Noto Sans CJK SC", response.text)

    def test_internal_share_page_returns_404_when_missing(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=None):
            response = client.get("/internal/share/player/999", headers={"X-Internal-Share-Token": "share-secret"})

        self.assertEqual(response.status_code, 404)

    def test_internal_share_page_requires_token_when_configured(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=_sample_player_detail()):
            response = client.get("/internal/share/player/24048100")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "internal_share_token_required")

    def test_internal_share_page_returns_503_when_token_not_configured(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db))
        client = TestClient(app)

        response = client.get("/internal/share/player/24048100")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "internal_share_not_configured")
