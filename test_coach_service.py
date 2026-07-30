import unittest
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Coach, CoachAccount, CoachHonor, CoachReactionEvent, CoachReactionSummary, CoachSession, Team
from schemas_write import (
    CoachAccountUpsertRequest,
    CoachHonorUpdateRequest,
    CoachLoginRequest,
    CoachMergeRequest,
    CoachPasswordChangeRequest,
    CoachQqBindingRequest,
    CoachTeamAssignmentRequest,
    CoachUpdateRequest,
)
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
        self.assertEqual(self.db.query(Team).filter(Team.name == "Alpha").one().manager, "Coach A+")

    def test_assign_coach_team_updates_team_manager_and_unbinds_previous_coach(self):
        payload = coach_service.get_coaches(self.db)
        coach_a = next(item for item in payload.coaches if item.nickname == "Coach A")
        beta = self.db.query(Team).filter(Team.name == "Beta").one()

        coach_service.assign_coach_team(
            self.db,
            "admin",
            coach_a.uid,
            CoachTeamAssignmentRequest(team_id=beta.id),
            lambda *_args: None,
        )

        previous_beta_coach = self.db.query(Coach).filter(Coach.nickname == "Coach B").one()
        self.assertIsNone(previous_beta_coach.team_id)
        self.assertEqual(beta.manager, "Coach A")
        self.assertEqual(self.db.query(Team).filter(Team.name == "Alpha").one().manager, "-")

    def test_merge_coach_moves_profile_data_reactions_and_selected_account(self):
        payload = coach_service.get_coaches(self.db)
        source = next(item for item in payload.coaches if item.nickname == "Coach A")
        target = next(item for item in payload.coaches if item.nickname == "Coach B")
        source_row = self.db.query(Coach).filter(Coach.uid == source.uid).one()
        target_row = self.db.query(Coach).filter(Coach.uid == target.uid).one()
        source_row.team_id = None
        source_row.team_name = None
        source_row.level = None
        target_row.bio = None
        source_row.bio = "旧资料"
        self.db.add_all([
            CoachAccount(coach_uid=source.uid, username="old-login", password_hash="old-hash"),
            CoachAccount(coach_uid=target.uid, username="new-login", password_hash="new-hash"),
            CoachHonor(coach_uid=source.uid, honor="冠军"),
            CoachReactionSummary(coach_uid=source.uid, flowers=2, eggs=3),
            CoachReactionSummary(coach_uid=target.uid, flowers=5, eggs=7),
            CoachReactionEvent(coach_uid=source.uid, visitor_token="visitor", reaction_type="flower", created_at=datetime.now()),
        ])
        self.db.commit()

        response = coach_service.merge_coach(
            self.db,
            "admin",
            source.uid,
            CoachMergeRequest(target_coach_uid=target.uid),
            lambda *_args: None,
        )

        self.assertTrue(response["success"])
        self.assertIsNone(self.db.query(Coach).filter(Coach.uid == source.uid).first())
        self.assertEqual(self.db.query(Coach).filter(Coach.uid == target.uid).one().bio, "旧资料")
        self.assertEqual(self.db.query(CoachHonor).one().coach_uid, target.uid)
        self.assertEqual(self.db.query(CoachReactionEvent).one().coach_uid, target.uid)
        summary = self.db.query(CoachReactionSummary).filter(CoachReactionSummary.coach_uid == target.uid).one()
        self.assertEqual((summary.flowers, summary.eggs), (7, 10))
        account = self.db.query(CoachAccount).one()
        self.assertEqual((account.coach_uid, account.username), (target.uid, "new-login"))

    def test_new_account_requires_password_change_then_can_bind_and_login_with_qq(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid
        coach_service.upsert_coach_account(
            self.db,
            "admin",
            coach_uid,
            CoachAccountUpsertRequest(username="coach-login", password="default123"),
            lambda *_args: None,
        )

        token, identity = coach_service.login_coach(self.db, CoachLoginRequest(username="coach-login", password="default123"))
        self.assertTrue(identity.must_change_password)
        coach_service.change_own_coach_password(
            self.db,
            token,
            CoachPasswordChangeRequest(current_password="default123", new_password="private456"),
            lambda *_args: None,
        )
        with self.assertRaises(HTTPException) as blocked:
            coach_service.update_own_coach_profile(
                self.db,
                token,
                CoachUpdateRequest(title="不应保存"),
                lambda *_args: None,
            )
        self.assertEqual(blocked.exception.status_code, 403)
        coach_service.bind_own_coach_qq(
            self.db,
            token,
            CoachQqBindingRequest(qq_number="12345678", current_password="private456"),
            lambda *_args: None,
        )

        _qq_token, qq_identity = coach_service.login_coach(
            self.db,
            CoachLoginRequest(username="12345678", password="private456"),
        )
        self.assertFalse(qq_identity.must_change_password)
        self.assertEqual(qq_identity.qq_number, "12345678")

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

    def test_upsert_coach_account_preserves_blank_password_and_updates_work_permissions(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid

        coach_service.upsert_coach_account(
            self.db,
            "admin",
            coach_uid,
            CoachAccountUpsertRequest(username="coach-a", password="secret123", can_manage_schedule=True),
            lambda *_args: None,
        )
        account = self.db.query(CoachAccount).filter(CoachAccount.coach_uid == coach_uid).one()
        original_hash = account.password_hash
        token, identity = coach_service.login_coach(self.db, CoachLoginRequest(username="coach-a", password="secret123"))

        self.assertTrue(identity.can_manage_schedule)
        self.assertTrue(self.db.query(CoachSession).filter(CoachSession.token == token).first())

        coach_service.upsert_coach_account(
            self.db,
            "admin",
            coach_uid,
            CoachAccountUpsertRequest(
                username="coach-a",
                password="",
                can_manage_suspensions=True,
                can_manage_candidate_lists=True,
            ),
            lambda *_args: None,
        )
        account = self.db.query(CoachAccount).filter(CoachAccount.coach_uid == coach_uid).one()

        self.assertEqual(account.password_hash, original_hash)
        self.assertEqual(self.db.query(CoachSession).filter(CoachSession.coach_uid == coach_uid).count(), 0)

        _token, identity = coach_service.login_coach(self.db, CoachLoginRequest(username="coach-a", password="secret123"))
        self.assertFalse(identity.can_manage_schedule)
        self.assertTrue(identity.can_manage_suspensions)
        self.assertTrue(identity.can_manage_candidate_lists)

    def test_coach_session_identity_includes_work_permissions(self):
        payload = coach_service.get_coaches(self.db)
        coach_uid = payload.coaches[0].uid
        coach_service.upsert_coach_account(
            self.db,
            "admin",
            coach_uid,
            CoachAccountUpsertRequest(
                username="coach-b",
                password="secret123",
                can_manage_schedule=True,
                can_manage_candidate_lists=True,
            ),
            lambda *_args: None,
        )
        token, _identity = coach_service.login_coach(self.db, CoachLoginRequest(username="coach-b", password="secret123"))

        identity = coach_service.get_coach_session_identity(self.db, token)

        self.assertTrue(identity.authenticated)
        self.assertTrue(identity.can_manage_schedule)
        self.assertFalse(identity.can_manage_suspensions)
        self.assertTrue(identity.can_manage_candidate_lists)

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
