import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from services import project_update_service


class ProjectUpdateServiceTests(unittest.TestCase):
    def test_parse_changelog_sections_into_entries(self):
        with TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "CHANGELOG.md"
            changelog_path.write_text(
                "\n".join(
                    [
                        "# Changelog",
                        "",
                        "## [Unreleased]",
                        "",
                        "### Refactored",
                        "- Split read service presenters",
                        "- Added footer links",
                        "",
                        "## [0.2.1] - 2026-03-25",
                        "",
                        "### Docs",
                        "- Updated deploy manual",
                    ]
                ),
                encoding="utf-8",
            )

            entries = project_update_service.list_project_updates(changelog_path=changelog_path)

        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[0].is_unreleased)
        self.assertEqual(entries[0].sections[0].heading, "Refactored")
        self.assertIn("Split read service presenters", entries[0].sections[0].items)
        self.assertEqual(entries[1].version, "0.2.1")
        self.assertEqual(entries[1].release_date, "2026-03-25")


if __name__ == "__main__":
    unittest.main()
