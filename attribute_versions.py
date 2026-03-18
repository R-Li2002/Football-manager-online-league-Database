from __future__ import annotations

import re
from pathlib import Path


DEFAULT_ATTRIBUTE_DATA_VERSION = "2600"
ATTRIBUTE_DATA_VERSION_PATTERN = re.compile(r"(?<!\d)(\d{4})(?!\d)")


def normalize_attribute_data_version(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def infer_attribute_data_version(path: str | Path | None, default: str = DEFAULT_ATTRIBUTE_DATA_VERSION) -> str:
    source_name = Path(path).name if path is not None else ""
    match = ATTRIBUTE_DATA_VERSION_PATTERN.search(source_name)
    return match.group(1) if match else default


def sort_attribute_versions(versions: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    normalized_versions = {
        normalized
        for value in versions
        if (normalized := normalize_attribute_data_version(value))
    }

    def version_key(version: str) -> tuple[int, int, str]:
        if version.isdigit():
            return (0, -int(version), version)
        return (1, 0, version.lower())

    return sorted(normalized_versions, key=version_key)


def pick_default_attribute_version(versions: list[str] | tuple[str, ...] | set[str]) -> str:
    sorted_versions = sort_attribute_versions(versions)
    return sorted_versions[0] if sorted_versions else DEFAULT_ATTRIBUTE_DATA_VERSION
