import unittest
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import CupMatch, HomePromotion, Match, Team
from schemas_read import WorkspaceIdentityResponse
from schemas_write import HomePromotionUpsertRequest
from services import home_promotion_asset_service, home_promotion_service


class HomePromotionServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.identity = WorkspaceIdentityResponse(
            principal_id="admin:test",
            source="admin_account",
            account_type="administrator",
            username="test",
            display_name="test",
            is_full_admin=True,
            capabilities=[],
            capability_labels=[],
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_crud_and_public_schedule_filter(self):
        created = home_promotion_service.create_promotion(
            self.db,
            self.identity,
            HomePromotionUpsertRequest(title="联赛公告", body="正文", theme="blue"),
        )
        self.assertEqual(created.title, "联赛公告")
        self.assertEqual(created.display_mode, "board")
        self.assertEqual(len(home_promotion_service.list_public_promotions(self.db)), 1)

        future = datetime.now() + timedelta(days=1)
        updated = home_promotion_service.update_promotion(
            self.db,
            self.identity,
            created.id,
            HomePromotionUpsertRequest(title="定时公告", starts_at=future),
        )
        self.assertEqual(updated.title, "定时公告")
        self.assertEqual(home_promotion_service.list_public_promotions(self.db), [])

        result = home_promotion_service.delete_promotion(self.db, self.identity, created.id)
        self.assertTrue(result["success"])
        self.assertEqual(self.db.query(HomePromotion).count(), 0)

    def test_public_schedule_uses_shanghai_league_time(self):
        league_now = datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
        home_promotion_service.create_promotion(
            self.db,
            self.identity,
            HomePromotionUpsertRequest(
                title="北京时间公告",
                starts_at=league_now - timedelta(minutes=1),
                ends_at=league_now + timedelta(minutes=1),
            ),
        )
        rows = home_promotion_service.list_public_promotions(self.db)
        self.assertEqual([item.title for item in rows], ["北京时间公告"])

    def test_tab_targets_cover_main_site_sections(self):
        targets = [
            "team", "players", "competition:standings", "competition:schedule:甲级",
            "competition:playerRankings:乙级", "database:tactics",
        ]
        for index, target in enumerate(targets):
            created = home_promotion_service.create_promotion(
                self.db,
                self.identity,
                HomePromotionUpsertRequest(
                    title=f"站内目标 {index}", action_kind="tab", action_label="查看", action_target=target,
                ),
            )
            self.assertEqual(created.action_target, target)

    def test_modal_promotion_delivery_mode_is_preserved(self):
        created = home_promotion_service.create_promotion(
            self.db,
            self.identity,
            HomePromotionUpsertRequest(title="教练欢迎", display_mode="modal"),
        )
        self.assertEqual(created.display_mode, "modal")
        public = home_promotion_service.list_public_promotions(self.db)
        self.assertEqual(public[0].display_mode, "modal")

    def test_sync_cup_champion_creates_editable_promotion(self):
        self.db.add(Team(id=7, name="R. Madrid", manager="HEIGO", level="超级", logo_path="/rm.png"))
        self.db.add(
            CupMatch(
                competition="champions_cup",
                stage="final",
                slot_no=1,
                winner_team_id=7,
                winner_team_name="R. Madrid",
                home_score=4,
                away_score=2,
                status="played",
                updated_at=datetime.now(),
            )
        )
        self.db.commit()

        rows = home_promotion_service.sync_cup_champions(self.db, self.identity)
        champion = next(item for item in rows if item.source_type == "cup_champion")
        self.assertIn("R. Madrid", champion.title)
        self.assertEqual(champion.action_target, "competition:standings:冠军杯")
        self.assertEqual(champion.image_url, "/rm.png")

    def test_sync_league_champion_requires_complete_34_rounds(self):
        self.db.add_all([
            Team(id=1, name="Champion FC", manager="Coach A", level="超级", logo_path="/champion.png"),
            Team(id=2, name="Runner FC", manager="Coach B", level="超级"),
        ])
        for round_no in range(1, 35):
            self.db.add(
                Match(
                    season_label="87",
                    level="超级",
                    round_no=round_no,
                    home_team_id=1,
                    home_team_name="Champion FC",
                    away_team_id=2,
                    away_team_name="Runner FC",
                    home_score=2,
                    away_score=0,
                    status="played",
                )
            )
        self.db.commit()

        rows = home_promotion_service.sync_league_champions(self.db, self.identity)
        champion = next(item for item in rows if item.source_type == "league_champion")
        self.assertEqual(champion.title, "Champion FC 荣膺超级联赛冠军")
        self.assertEqual(champion.action_target, "competition:standings:超级")
        self.assertIn("34 轮战罢", champion.body)

    def test_local_promotion_image_upload_is_converted_to_webp(self):
        source = io.BytesIO()
        Image.new("RGB", (640, 360), "#7454e8").save(source, format="PNG")
        source.seek(0)
        upload = UploadFile(filename="promotion.png", file=source, headers={"content-type": "image/png"})
        result = home_promotion_asset_service.save_promotion_image(self.identity, upload)
        target = Path(f".{result['image_url']}")
        try:
            self.assertTrue(result["image_url"].endswith(".webp"))
            self.assertTrue(target.exists())
            self.assertEqual((result["width"], result["height"]), (640, 360))
        finally:
            target.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
