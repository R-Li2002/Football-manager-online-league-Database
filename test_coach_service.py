import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Coach, CoachHonor, Team
from schemas_write import CoachHonorUpdateRequest, CoachUpdateRequest
from services import coach_service


class CoachServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        self.db.add_all(
            [
                Team(name="Alpha", level="超级", manager="Coach A"),
                Team(name="Beta", level="甲级", manager="Coach B"),
                Team(name="Gamma", level="乙级", manager="Coach C"),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_get_coaches_syncs_from_team_managers(self):
        payload = coach_service.get_coaches(self.db)

        self.assertEqual(payload.levels, ["超级", "甲级", "乙级"])
        self.assertEqual(len(payload.coaches), 3)
        self.assertTrue(self.db.query(Coach).filter(Coach.nickname == "Coach A").first())

    def test_refresh_assignments_rebinds_changed_team_manager(self):
        coach_service.get_coaches(self.db)
        team = self.db.query(Team).filter(Team.name == "Alpha").one()
        team.manager = "Coach A2"
        self.db.commit()

        coach_service.refresh_coach_assignments(self.db)

        old_coach = self.db.query(Coach).filter(Coach.nickname == "Coach A").one()
        new_coach = self.db.query(Coach).filter(Coach.nickname == "Coach A2").one()
        self.assertIsNone(old_coach.team_id)
        self.assertEqual(new_coach.team_name, "Alpha")

    def test_update_profile_and_honor_are_returned_in_detail(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = next(item.uid for item in payload.coaches if item.nickname == "Coach A")

        coach_service.update_coach_profile(
            self.db,
            "editor",
            coach_uid,
            CoachUpdateRequest(nickname="Coach A+", title="冠军教头", bio="擅长淘汰赛。"),
            lambda *_args: None,
        )
        coach_service.upsert_coach_honor(
            self.db,
            "editor",
            CoachHonorUpdateRequest(coach_uid=coach_uid, season="S1", competition="冠军杯", honor="冠军", description="首届冠军"),
            lambda *_args: None,
        )

        detail = coach_service.get_coach_detail(self.db, coach_uid)
        self.assertEqual(detail.nickname, "Coach A+")
        self.assertEqual(detail.title, "冠军教头")
        self.assertEqual(detail.honors[0].honor, "冠军")

    def test_delete_honor(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid
        coach_service.upsert_coach_honor(
            self.db,
            "editor",
            CoachHonorUpdateRequest(coach_uid=coach_uid, edition=85, competition="甲级联赛", placement="冠军", honor="冠军"),
            lambda *_args: None,
        )
        honor = self.db.query(CoachHonor).one()
        self.assertEqual(honor.edition, 85)
        self.assertEqual(honor.placement, "冠军")

        coach_service.delete_coach_honor(self.db, "editor", honor.id, lambda *_args: None)

        self.assertEqual(self.db.query(CoachHonor).count(), 0)

    def test_honors_are_ordered_by_edition_ascending(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid
        for edition in [86, 84, 85]:
            coach_service.upsert_coach_honor(
                self.db,
                "editor",
                CoachHonorUpdateRequest(
                    coach_uid=coach_uid,
                    edition=edition,
                    competition="冠军杯",
                    placement="冠军",
                    honor="冠军",
                ),
                lambda *_args: None,
            )

        detail = coach_service.get_coach_detail(self.db, coach_uid)

        self.assertEqual([honor.edition for honor in detail.honors], [84, 85, 86])

    def test_newcomer_competition_honor_is_allowed(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid

        coach_service.upsert_coach_honor(
            self.db,
            "editor",
            CoachHonorUpdateRequest(coach_uid=coach_uid, edition=85, competition="新人赛", placement="冠军", honor="冠军"),
            lambda *_args: None,
        )

        detail = coach_service.get_coach_detail(self.db, coach_uid)
        self.assertEqual(detail.honors[0].competition, "新人赛")
        self.assertEqual(detail.honors[0].placement, "冠军")

    def test_coach_reaction_uses_cooldown(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid

        first = coach_service.record_coach_reaction(self.db, coach_uid, "visitor-1", "flower")
        second = coach_service.record_coach_reaction(self.db, coach_uid, "visitor-1", "egg")

        self.assertTrue(first.accepted)
        self.assertFalse(second.accepted)
        self.assertEqual(second.summary.flowers, 1)

    def test_save_avatar_updates_avatar_path(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid
        from PIL import Image

        image_bytes = BytesIO()
        Image.new("RGB", (300, 300), color=(30, 120, 180)).save(image_bytes, format="PNG")
        image_bytes.seek(0)
        avatar = UploadFile(filename="avatar.png", file=image_bytes, headers={"content-type": "image/png"})

        response = coach_service.save_coach_avatar(self.db, "editor", coach_uid, avatar, lambda *_args: None)

        self.assertTrue(response["success"])
        self.assertTrue(response["avatar_path"].startswith("/static/uploads/coaches/"))
        detail = coach_service.get_coach_detail(self.db, coach_uid)
        self.assertEqual(detail.avatar_path, response["avatar_path"])

    def test_save_avatar_deletes_previous_avatar_for_same_coach(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid
        from PIL import Image

        def build_avatar(color):
            image_bytes = BytesIO()
            Image.new("RGB", (300, 300), color=color).save(image_bytes, format="PNG")
            image_bytes.seek(0)
            return UploadFile(filename="avatar.png", file=image_bytes, headers={"content-type": "image/png"})

        with TemporaryDirectory() as temp_dir, patch.object(coach_service, "COACH_AVATAR_ROOT", Path(temp_dir)):
            first = coach_service.save_coach_avatar(self.db, "editor", coach_uid, build_avatar((30, 120, 180)), lambda *_args: None)
            first_file = Path(temp_dir) / first["avatar_path"].rsplit("/", 1)[-1]
            self.assertTrue(first_file.exists())

            second = coach_service.save_coach_avatar(self.db, "editor", coach_uid, build_avatar((180, 80, 30)), lambda *_args: None)
            second_file = Path(temp_dir) / second["avatar_path"].rsplit("/", 1)[-1]

            self.assertNotEqual(first["avatar_path"], second["avatar_path"])
            self.assertFalse(first_file.exists())
            self.assertTrue(second_file.exists())


if __name__ == "__main__":
    unittest.main()
