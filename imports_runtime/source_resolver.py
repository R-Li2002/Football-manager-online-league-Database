from __future__ import annotations

from pathlib import Path

from imports_runtime.constants import ATTRIBUTE_SOURCE_PATTERNS

def choose_latest_file(root_dir: Path, patterns: list[str], label: str, warnings: list[str]) -> Path:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(root_dir.glob(pattern))
    candidates = [path for path in candidates if path.is_file() and not path.name.startswith("~$")]
    if not candidates:
        raise FileNotFoundError(f"未找到{label}文件，搜索模式: {patterns}")
    candidates = sorted(set(candidates), key=lambda path: (path.stat().st_mtime, path.stat().st_size, path.name), reverse=True)
    if len(candidates) > 1:
        warnings.append(f"{label}存在多个候选文件，已自动选择最新文件: {candidates[0].name}")
    return candidates[0]

def resolve_explicit_path(path_value: str | Path, root_dir: Path, label: str) -> Path:
    resolved = Path(path_value)
    if not resolved.is_absolute():
        resolved = root_dir / resolved
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"{label}文件不存在: {resolved}")
    return resolved

def resolve_input_files(workbook_path: str | Path | None, attributes_csv_path: str | Path | None, root_dir: Path) -> tuple[Path, Path, list[str]]:
    warnings: list[str] = []
    workbook = (
        resolve_explicit_path(workbook_path, root_dir, "league workbook")
        if workbook_path
        else choose_latest_file(root_dir, ["*HEIGO*.xlsx"], "league workbook", warnings)
    )
    attributes_path = (
        resolve_explicit_path(attributes_csv_path, root_dir, "player attributes")
        if attributes_csv_path
        else choose_latest_file(root_dir, ATTRIBUTE_SOURCE_PATTERNS, "player attributes", warnings)
    )
    return workbook, attributes_path, warnings
