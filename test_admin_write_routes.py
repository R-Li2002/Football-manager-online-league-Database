import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import AdminUser, Team
from routers.admin_write_routes import build_admin_write_router
from schemas_write import AdminActionResponse, SiteNoteUpdateRequest


class AdminWriteRoutesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        self.db.add_all(
            [
                AdminUser(username="HEIGO01", password_hash="unused", role="admin"),
                Team(id=39, name="Arsenal", level="乙级", manager="囊个"),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_site_note_route_resolves_team_level_and_delegates_update(self):
        router = build_admin_write_router(
            lambda: self.db,
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda *_args, **_kwargs: None,
            lambda *_args, **_kwargs: None,
            lambda *_args: None,
        )
        endpoint = next(
            route.endpoint
            for route in router.routes
            if route.path == "/api/admin/site-notes/{note_key:path}" and "PATCH" in route.methods
        )
        request = SiteNoteUpdateRequest(text="", round_no=1)
        expected = AdminActionResponse(success=True, message="注释已保存")

        with patch(
            "routers.admin_write_routes.admin_write_service.update_site_note",
            return_value=expected,
        ) as update_site_note:
            response = endpoint(
                note_key="competition.suspensions.team.39",
                request=request,
                db=self.db,
                admin="HEIGO01",
            )

        self.assertEqual(response, expected)
        update_site_note.assert_called_once()
        self.assertEqual(update_site_note.call_args.args[:4], (self.db, "HEIGO01", "competition.suspensions.team.39", request))

    def test_draw_and_archive_routes_use_separate_permissions(self):
        draw_guard = lambda: "draw-operator"
        archive_guard = lambda: "archive-operator"
        router = build_admin_write_router(
            lambda: self.db,
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda: "HEIGO01",
            lambda *_args, **_kwargs: None,
            lambda *_args, **_kwargs: None,
            lambda *_args: None,
            verify_draw_manager=draw_guard,
            verify_archive_manager=archive_guard,
        )
        draw_route = next(route for route in router.routes if route.path == "/api/admin/draws")
        draw_delete_route = next(
            route
            for route in router.routes
            if route.path == "/api/admin/draws/{session_id}" and "DELETE" in route.methods
        )
        archive_route = next(route for route in router.routes if route.path == "/api/admin/season-archives")
        draw_dependencies = {dependency.call for dependency in draw_route.dependant.dependencies}
        draw_delete_dependencies = {dependency.call for dependency in draw_delete_route.dependant.dependencies}
        archive_dependencies = {dependency.call for dependency in archive_route.dependant.dependencies}

        self.assertIn(draw_guard, draw_dependencies)
        self.assertNotIn(archive_guard, draw_dependencies)
        self.assertIn(draw_guard, draw_delete_dependencies)
        self.assertIn(archive_guard, archive_dependencies)
        self.assertNotIn(draw_guard, archive_dependencies)


if __name__ == "__main__":
    unittest.main()
