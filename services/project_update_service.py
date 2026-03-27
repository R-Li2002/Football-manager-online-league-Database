from __future__ import annotations

import re
from pathlib import Path

from schemas_read import ProjectUpdateEntryResponse, ProjectUpdateSectionResponse

CHANGELOG_PATH = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
RELEASE_HEADING_RE = re.compile(r"^##\s+\[(?P<version>[^\]]+)\](?:\s*-\s*(?P<date>.+))?$")
SECTION_HEADING_RE = re.compile(r"^###\s+(?P<title>.+)$")


def list_project_updates(limit: int = 20, *, changelog_path: str | Path | None = None) -> list[ProjectUpdateEntryResponse]:
    source_path = Path(changelog_path) if changelog_path else CHANGELOG_PATH
    if not source_path.exists():
        return []

    entries: list[dict] = []
    current_entry: dict | None = None
    current_section: dict | None = None

    for raw_line in source_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        release_match = RELEASE_HEADING_RE.match(line)
        if release_match:
            current_entry = {
                "version": release_match.group("version"),
                "release_date": (release_match.group("date") or "").strip() or None,
                "is_unreleased": release_match.group("version") == "Unreleased",
                "sections": [],
            }
            entries.append(current_entry)
            current_section = None
            continue

        if current_entry is None:
            continue

        section_match = SECTION_HEADING_RE.match(line)
        if section_match:
            current_section = {"heading": section_match.group("title"), "items": []}
            current_entry["sections"].append(current_section)
            continue

        if line.startswith("- "):
            if current_section is None:
                current_section = {"heading": "Summary", "items": []}
                current_entry["sections"].append(current_section)
            current_section["items"].append(line[2:].strip())

    parsed_entries = [
        ProjectUpdateEntryResponse(
            version=entry["version"],
            release_date=entry["release_date"],
            is_unreleased=entry["is_unreleased"],
            sections=[ProjectUpdateSectionResponse(**section) for section in entry["sections"]],
        )
        for entry in entries
        if entry["sections"]
    ]
    return parsed_entries[: max(1, limit)]
