from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session, sessionmaker

from auth_utils import hash_password
from database import engine, init_database
from league_settings import create_league_info_record, get_growth_age_limit
from models import AdminUser, LeagueInfo, Player, PlayerAttribute, Team, TransferLog
from services.league_service import (
    PERSISTED_TEAM_STAT_SCOPES,
    TEAM_CACHE_REFRESH_MODE_FULL_RECALC,
    recalculate_team_stats,
    refresh_player_financials,
)

WORKBOOK_SHEET_OVERVIEW = "信息总览"
WORKBOOK_SHEET_LEAGUE_PLAYERS = "联赛名单"
WORKBOOK_SHEET_PLAYER_TEAM_MAP = "球员对应球队"
HIDDEN_SEA_TEAM_NAME = "85大海"
HIDDEN_SEA_TEAM_LEVEL = "隐藏"
HIDDEN_SEA_TEAM_MANAGER = "系统"

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\xa0]")
GK_COEFFICIENT_RE = re.compile(r"GK系数为\s*([0-9.]+)")

SUPPORTED_INFO_KEY_ALIASES = {
    "8M名额": "8M名额系数",
    "7M名额": "7M名额系数",
    "可成长名额": "可成长名额系数",
    "非名PA6M": "非名PA6M系数",
    "非名身价1M": "非名身价1M系数",
    "非名其他": "非名其他系数",
}

DEFAULT_LEAGUE_INFO_VALUES = {
    "届数": 85,
    "本版首届": 84,
    "成长年龄上限": 24,
    "超级级工资帽": 9.4,
    "甲级级工资帽": 8.9,
    "乙级级工资帽": 8.6,
    "总工资": 446.71,
    "总平均工资": 8.27,
    "总身价": 4876.5,
    "总平均身价": 261.53,
    "身价极差": 30.0,
    "总平均CA": 7638.88,
    "CA极差": 31.4,
    "总平均PA": 8473.48,
    "PA极差": 11.72,
    "总平均成长": 83.17,
    "8M名额系数": 1.5,
    "7M名额系数": 1.3,
    "可成长名额系数": 1.1,
    "非名PA6M系数": 0.9,
    "非名身价1M系数": 1.0,
    "非名其他系数": 0.7,
    "GK系数": 1.0,
}

TEAM_COLUMN_ALIASES = {
    "name": ["球队名"],
    "manager": ["主教"],
    "level": ["级别"],
    "extra_wage": ["额外工资"],
    "after_tax": ["税后"],
    "notes": ["备注"],
}

PLAYER_COLUMN_ALIASES = {
    "uid": ["编号"],
    "name": ["姓名"],
    "age": ["年龄"],
    "initial_ca": ["初始CA"],
    "ca": ["当前CA"],
    "pa": ["PA"],
    "position": ["位置"],
    "nationality": ["国籍"],
    "team_name": ["联赛球队", "俱乐部", "更新俱乐部"],
}

PLAYER_TEAM_MAP_COLUMN_ALIASES = {
    "uid": ["UID"],
    "team_name": ["球队"],
    "position": ["位置"],
}

ATTRIBUTE_COLUMN_ALIASES = {
    "uid": ["UID"],
    "name": ["姓名"],
    "position": ["位置"],
    "age": ["年龄"],
    "ca": ["ca"],
    "pa": ["pa"],
    "nationality": ["国籍"],
    "club": ["俱乐部"],
    "corner": ["角球"],
    "crossing": ["传中"],
    "dribbling": ["盘带"],
    "finishing": ["射门"],
    "first_touch": ["接球"],
    "free_kick": ["任意球"],
    "heading": ["头球"],
    "long_shots": ["远射"],
    "long_throws": ["界外球"],
    "marking": ["盯人"],
    "passing": ["传球"],
    "penalty": ["罚点球"],
    "tackling": ["抢断"],
    "technique": ["技术"],
    "aggression": ["侵略性"],
    "anticipation": ["预判"],
    "bravery": ["勇敢"],
    "composure": ["镇定"],
    "concentration": ["集中"],
    "decisions": ["决断"],
    "determination": ["意志力"],
    "flair": ["想象力"],
    "leadership": ["领导力"],
    "off_the_ball": ["无球跑动"],
    "positioning": ["防守站位"],
    "teamwork": ["团队合作"],
    "vision": ["视野"],
    "work_rate": ["工作投入"],
    "acceleration": ["爆发力"],
    "agility": ["灵活"],
    "balance": ["平衡"],
    "jumping": ["弹跳"],
    "natural_fitness": ["体质"],
    "pace": ["速度"],
    "stamina": ["耐力"],
    "strength": ["强壮"],
    "consistency": ["稳定"],
    "dirtiness": ["肮脏"],
    "important_matches": ["大赛"],
    "injury_proneness": ["伤病"],
    "versatility": ["多样"],
    "adaptability": ["适应性"],
    "ambition": ["雄心"],
    "controversy": ["争论"],
    "loyalty": ["忠诚"],
    "pressure": ["抗压能力"],
    "professionalism": ["职业"],
    "sportsmanship": ["体育道德"],
    "temperament": ["情绪控制"],
    "aerial_ability": ["制空能力"],
    "command_of_area": ["拦截传中"],
    "communication": ["沟通"],
    "eccentricity": ["神经指数"],
    "handling": ["手控球"],
    "kicking": ["大脚开球"],
    "one_on_ones": ["一对一"],
    "reflexes": ["反应"],
    "rushing_out": ["出击"],
    "tendency_to_punch": ["击球倾向"],
    "throwing": ["手抛球的能力"],
    "pos_gk": ["GK"],
    "pos_dl": ["DL"],
    "pos_dc": ["DC"],
    "pos_dr": ["DR"],
    "pos_wbl": ["WBL"],
    "pos_wbr": ["WBR"],
    "pos_dm": ["DM"],
    "pos_ml": ["ML"],
    "pos_mc": ["MC"],
    "pos_mr": ["MR"],
    "pos_aml": ["AML"],
    "pos_amc": ["AMC"],
    "pos_amr": ["AMR"],
    "pos_st": ["ST"],
    "height": ["身高"],
    "weight": ["体重"],
    "left_foot": ["左脚"],
    "right_foot": ["右脚"],
    "birth_date": ["出生日期"],
    "national_caps": ["国家队出场"],
    "national_goals": ["国家队进球"],
    "player_habits": ["球员习惯"],
}

TEAM_NAME_ALIASES = {
    "AFC Bournemouth": "Bournemouth",
    "Associazione Sportiva Roma": "As Roma",
    "Bayer 04 Leverkusen": "Bayer 04",
    "Blu-neri Milano": "Inter",
    "Brighton & Hove Albion": "Brighton",
    "Capitolini Celesti": "Lazio",
    "Casciavit Milano": "AC Milan",
    "Club Atlético Boca Juniors": "Boca",
    "Club Atlético Talleres de Córdoba": "Talleres",
    "Como 1907": "Como",
    "FC Bayern München": "FC Bayern",
    "FC Schalke 04": "Schalke 04",
    "Futebol Clube do Porto": "FC Porto",
    "Inter Miami CF": "Inter Miami",
    "Leicester City": "Leicester",
    "Manchester City": "Man City",
    "Manchester United": "Man UFC",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nottm Forest",
    "Olympique de Marseille": "OM",
    "Paris Saint-Germain": "Paris SG",
    "Parthenope": "Napoli",
    "RC Strasbourg Alsace": "Strasbourg",
    "Sheffield United": "Sheff Utd",
    "Sport Lisboa e Benfica": "Benfica",
    "Sporting Clube de Portugal": "Sporting CP",
    "Sportklub Sturm Graz": "Sturm Graz",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Zhejiang FC": "Zhejiang",
}

ERROR_DETAIL_SAMPLE_LIMIT = 50


@dataclass
class DatasetSummary:
    source: str
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        self.errors.append(message)


@dataclass
class ImportReport:
    workbook_path: str
    attributes_csv_path: str
    dry_run: bool
    strict_mode: bool
    committed: bool = False
    fatal_error: str | None = None
    datasets: dict[str, DatasetSummary] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        if self.fatal_error:
            return True
        return any(summary.errors for summary in self.datasets.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workbook_path": self.workbook_path,
            "attributes_csv_path": self.attributes_csv_path,
            "dry_run": self.dry_run,
            "strict_mode": self.strict_mode,
            "committed": self.committed,
            "fatal_error": self.fatal_error,
            "warnings": self.warnings,
            "datasets": {name: asdict(summary) for name, summary in self.datasets.items()},
        }


def normalize_header(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = ZERO_WIDTH_RE.sub("", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if hasattr(result, "shape"):
        return False
    try:
        return bool(result)
    except (TypeError, ValueError):
        return False


def clean_string(value: Any, default: str = "") -> str:
    if is_blank(value):
        return default
    return str(value).strip()


def parse_int(value: Any, field_name: str) -> int:
    if is_blank(value):
        raise ValueError(f"{field_name} 不能为空")
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 不是合法整数: {value}") from exc


def parse_optional_int(value: Any, default: int = 0) -> int:
    if is_blank(value):
        return default
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return default


def parse_optional_float(value: Any, default: float = 0.0) -> float:
    if is_blank(value):
        return default
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


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
        resolve_explicit_path(workbook_path, root_dir, "联机联赛 Excel")
        if workbook_path
        else choose_latest_file(root_dir, ["*HEIGO*.xlsx"], "联机联赛 Excel", warnings)
    )
    attributes_csv = (
        resolve_explicit_path(attributes_csv_path, root_dir, "球员属性 CSV")
        if attributes_csv_path
        else choose_latest_file(root_dir, ["*球员属性*.csv"], "球员属性 CSV", warnings)
    )
    return workbook, attributes_csv, warnings


def build_column_lookup(df: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in df.columns:
        normalized = normalize_header(column)
        if normalized and normalized not in lookup:
            lookup[normalized] = column
    return lookup


def resolve_column(df: pd.DataFrame, aliases: list[str], required: bool = True) -> str | None:
    lookup = build_column_lookup(df)
    for alias in aliases:
        resolved = lookup.get(normalize_header(alias))
        if resolved is not None:
            return resolved
    if required:
        raise KeyError(f"缺少列: {aliases}")
    return None


def apply_model_updates(instance: Any, field_values: dict[str, Any]) -> bool:
    changed = False
    for field_name, new_value in field_values.items():
        if getattr(instance, field_name) != new_value:
            setattr(instance, field_name, new_value)
            changed = True
    return changed


def dataset_summary(report: ImportReport, name: str, source: Path) -> DatasetSummary:
    summary = DatasetSummary(source=str(source))
    report.datasets[name] = summary
    return summary


def record_validation_issue(summary: DatasetSummary, issue_type: str, message: str, **issue_data: Any) -> None:
    summary.add_error(message)
    error_counts = summary.details.setdefault("error_counts", {})
    error_counts[issue_type] = error_counts.get(issue_type, 0) + 1
    error_samples = summary.details.setdefault("error_samples", {})
    samples = error_samples.setdefault(issue_type, [])
    if len(samples) < ERROR_DETAIL_SAMPLE_LIMIT:
        samples.append(
            {
                key: value
                for key, value in issue_data.items()
                if value not in (None, "", [], {})
            }
        )


def normalize_team_identifier(value: str) -> str:
    normalized = normalize_header(value).casefold()
    normalized = normalized.replace(".", "").replace("&", "and")
    return normalized


@lru_cache(maxsize=8)
def get_workbook_sheet_names(workbook_path: str) -> tuple[str, ...]:
    with pd.ExcelFile(workbook_path) as workbook:
        return tuple(workbook.sheet_names)


def resolve_sheet_name(workbook_path: Path, requested_sheet_name: str) -> str:
    normalized_requested = normalize_header(requested_sheet_name)
    sheet_names = get_workbook_sheet_names(str(workbook_path))
    for sheet_name in sheet_names:
        if normalize_header(sheet_name) == normalized_requested:
            return sheet_name
    raise KeyError(f"工作簿缺少工作表: {requested_sheet_name}；可用工作表: {list(sheet_names)}")


def load_excel(workbook_path: Path, sheet_name: str, header: int | None) -> pd.DataFrame:
    resolved_sheet_name = resolve_sheet_name(workbook_path, sheet_name)
    return pd.read_excel(workbook_path, sheet_name=resolved_sheet_name, header=header, dtype=object)


def resolve_team_name(team_name: str, teams_by_name: dict[str, Team], normalized_team_names: dict[str, str]) -> str:
    raw_team_name = clean_string(team_name)
    if not raw_team_name:
        return ""
    if raw_team_name in teams_by_name:
        return raw_team_name

    normalized = normalize_team_identifier(raw_team_name)
    direct_match = normalized_team_names.get(normalized)
    if direct_match:
        return direct_match

    aliased = TEAM_NAME_ALIASES.get(raw_team_name)
    if aliased:
        return aliased

    alias_match = normalized_team_names.get(normalize_team_identifier(raw_team_name))
    if alias_match:
        return alias_match

    return raw_team_name


def load_player_team_overrides(workbook_path: Path, summary: DatasetSummary) -> dict[int, dict[str, str]]:
    try:
        df = load_excel(workbook_path, WORKBOOK_SHEET_PLAYER_TEAM_MAP, header=0)
    except Exception as exc:
        summary.add_warning(f"未加载 {WORKBOOK_SHEET_PLAYER_TEAM_MAP}，将仅使用联赛名单中的球队/位置: {exc}")
        return {}

    try:
        resolved_columns = {
            field_name: resolve_column(df, aliases, required=field_name == "uid")
            for field_name, aliases in PLAYER_TEAM_MAP_COLUMN_ALIASES.items()
        }
    except KeyError as exc:
        summary.add_warning(f"{WORKBOOK_SHEET_PLAYER_TEAM_MAP} 缺少关键列，跳过映射回退: {exc}")
        return {}

    overrides: dict[int, dict[str, str]] = {}
    duplicate_uids: set[int] = set()
    for row_index, row in df.iterrows():
        uid_value = row.get(resolved_columns["uid"])
        if is_blank(uid_value):
            continue
        try:
            uid = parse_int(uid_value, "UID")
        except ValueError:
            continue

        override = {
            "team_name": clean_string(row.get(resolved_columns.get("team_name"))),
            "position": clean_string(row.get(resolved_columns.get("position"))),
        }
        if not override["team_name"] and not override["position"]:
            continue
        if uid in overrides:
            duplicate_uids.add(uid)
        overrides[uid] = override

    if duplicate_uids:
        summary.add_warning(f"{WORKBOOK_SHEET_PLAYER_TEAM_MAP} 中存在重复 UID，已按最后一条记录覆盖: {sorted(duplicate_uids)[:10]}")
    summary.details["player_team_overrides"] = len(overrides)
    return overrides


def import_league_info(db: Session, workbook_path: Path, report: ImportReport) -> None:
    summary = dataset_summary(report, "league_info", workbook_path)
    try:
        df = load_excel(workbook_path, WORKBOOK_SHEET_OVERVIEW, header=None)
    except Exception as exc:
        summary.add_error(f"读取 {WORKBOOK_SHEET_OVERVIEW} 失败: {exc}")
        return

    existing_records = {record.key: record for record in db.query(LeagueInfo).all()}
    extracted_values: dict[str, Any] = {}

    for row_index, row in df.iterrows():
        raw_key = clean_string(row.iloc[0] if len(row) > 0 else "")
        if not raw_key:
            continue
        normalized_key = SUPPORTED_INFO_KEY_ALIASES.get(raw_key, raw_key)
        raw_value = row.iloc[1] if len(row) > 1 else None

        if normalized_key in DEFAULT_LEAGUE_INFO_VALUES and not is_blank(raw_value):
            extracted_values[normalized_key] = raw_value
            continue

        gk_match = GK_COEFFICIENT_RE.search(raw_key)
        if gk_match:
            extracted_values["GK系数"] = gk_match.group(1)

    for key, default_value in DEFAULT_LEAGUE_INFO_VALUES.items():
        raw_value = extracted_values.get(key, default_value)
        if key not in extracted_values:
            summary.add_warning(f"{key} 未在 Excel 中找到，已回退到默认值 {default_value}")
        existing = existing_records.get(key)
        if existing is None:
            db.add(create_league_info_record(key, raw_value))
            summary.created += 1
            continue

        before = existing.value
        existing.set_typed_value(raw_value)
        if existing.value != before:
            summary.updated += 1
        else:
            summary.unchanged += 1

    db.flush()


def import_teams(db: Session, workbook_path: Path, report: ImportReport) -> set[str]:
    summary = dataset_summary(report, "teams", workbook_path)
    try:
        df = load_excel(workbook_path, WORKBOOK_SHEET_OVERVIEW, header=1)
    except Exception as exc:
        summary.add_error(f"读取 {WORKBOOK_SHEET_OVERVIEW} 团队数据失败: {exc}")
        return set()

    try:
        team_name_column = resolve_column(df, TEAM_COLUMN_ALIASES["name"])
        level_column = resolve_column(df, TEAM_COLUMN_ALIASES["level"])
        manager_column = resolve_column(df, TEAM_COLUMN_ALIASES["manager"], required=False)
        extra_wage_column = resolve_column(df, TEAM_COLUMN_ALIASES["extra_wage"], required=False)
        after_tax_column = resolve_column(df, TEAM_COLUMN_ALIASES["after_tax"], required=False)
        notes_column = resolve_column(df, TEAM_COLUMN_ALIASES["notes"], required=False)
    except KeyError as exc:
        summary.add_error(str(exc))
        return set()

    existing_teams = {team.name: team for team in db.query(Team).all()}
    source_team_names: set[str] = set()

    for row_index, row in df.iterrows():
        excel_row = row_index + 3
        team_name = clean_string(row.get(team_name_column))
        level = clean_string(row.get(level_column))
        if not team_name and not level:
            continue
        if not team_name:
            summary.add_error(f"Excel 行 {excel_row}: 球队名为空")
            summary.skipped += 1
            continue
        if team_name in source_team_names:
            summary.add_error(f"Excel 行 {excel_row}: 球队名重复 {team_name}")
            summary.skipped += 1
            continue
        source_team_names.add(team_name)

        if not level:
            summary.add_error(f"Excel 行 {excel_row}: 球队 {team_name} 缺少级别")
            summary.skipped += 1
            continue

        field_values = {
            "name": team_name,
            "manager": clean_string(row.get(manager_column), default="系统") if manager_column else "系统",
            "level": level,
            "extra_wage": parse_optional_float(row.get(extra_wage_column)) if extra_wage_column else 0.0,
            "after_tax": parse_optional_float(row.get(after_tax_column)) if after_tax_column else 0.0,
            "notes": clean_string(row.get(notes_column)) if notes_column else "",
        }

        existing = existing_teams.get(team_name)
        if existing is None:
            db.add(Team(**field_values))
            summary.created += 1
            continue

        if apply_model_updates(existing, field_values):
            summary.updated += 1
        else:
            summary.unchanged += 1

    sea_team = existing_teams.get(HIDDEN_SEA_TEAM_NAME) or db.query(Team).filter(Team.name == HIDDEN_SEA_TEAM_NAME).first()
    if sea_team is None:
        db.add(Team(name=HIDDEN_SEA_TEAM_NAME, manager=HIDDEN_SEA_TEAM_MANAGER, level=HIDDEN_SEA_TEAM_LEVEL, wage=0.0))
        summary.created += 1
        summary.details["sea_team"] = "created"
    else:
        if apply_model_updates(sea_team, {"manager": HIDDEN_SEA_TEAM_MANAGER, "level": HIDDEN_SEA_TEAM_LEVEL}):
            summary.updated += 1
            summary.details["sea_team"] = "updated"
        else:
            summary.unchanged += 1
            summary.details["sea_team"] = "unchanged"

    summary.details["source_visible_team_count"] = len(source_team_names)
    db.flush()
    return source_team_names


def cleanup_stale_visible_teams(db: Session, source_team_names: set[str], report: ImportReport) -> None:
    summary = dataset_summary(report, "team_cleanup", Path("<derived>"))
    if not source_team_names:
        summary.add_warning("No source teams were resolved; stale-team cleanup skipped.")
        return

    stale_candidates = (
        db.query(Team)
        .filter(Team.level != HIDDEN_SEA_TEAM_LEVEL)
        .filter(Team.name.not_in(source_team_names))
        .order_by(Team.id.asc())
        .all()
    )
    removed_team_names: list[str] = []
    blocked_team_names: list[str] = []

    for team in stale_candidates:
        has_players = (
            db.query(Player.uid)
            .filter((Player.team_id == team.id) | (Player.team_name == team.name))
            .first()
            is not None
        )
        has_logs = (
            db.query(TransferLog.id)
            .filter(
                (TransferLog.from_team_id == team.id)
                | (TransferLog.to_team_id == team.id)
                | (TransferLog.from_team == team.name)
                | (TransferLog.to_team == team.name)
            )
            .first()
            is not None
        )
        if has_players or has_logs:
            blocked_team_names.append(team.name)
            continue

        db.delete(team)
        removed_team_names.append(team.name)

    summary.updated = len(removed_team_names)
    summary.skipped = len(blocked_team_names)
    summary.details["candidate_count"] = len(stale_candidates)
    summary.details["removed_count"] = len(removed_team_names)
    summary.details["blocked_count"] = len(blocked_team_names)
    if removed_team_names:
        summary.details["removed_teams"] = removed_team_names
    if blocked_team_names:
        summary.details["blocked_teams"] = blocked_team_names
    db.flush()


def import_players(db: Session, workbook_path: Path, report: ImportReport, *, strict_mode: bool = True) -> None:
    summary = dataset_summary(report, "players", workbook_path)
    summary.details["strict_mode"] = strict_mode
    try:
        df = load_excel(workbook_path, WORKBOOK_SHEET_LEAGUE_PLAYERS, header=0)
    except Exception as exc:
        summary.add_error(f"读取 {WORKBOOK_SHEET_LEAGUE_PLAYERS} 失败: {exc}")
        return

    try:
        resolved_columns = {
            field_name: resolve_column(df, aliases, required=field_name in {"uid", "name", "age", "ca", "pa", "position", "team_name"})
            for field_name, aliases in PLAYER_COLUMN_ALIASES.items()
        }
        club_team_name_column = resolve_column(df, ["俱乐部"], required=False)
    except KeyError as exc:
        summary.add_error(str(exc))
        summary.details["missing_columns"] = [str(exc)]
        return

    existing_players = {player.uid: player for player in db.query(Player).all()}
    teams_by_name = {team.name: team for team in db.query(Team).all()}
    normalized_team_names = {normalize_team_identifier(team_name): team_name for team_name in teams_by_name}
    player_team_overrides = load_player_team_overrides(workbook_path, summary) if not strict_mode else {}
    seen_uids: set[int] = set()
    alias_team_hits = 0
    club_team_fallback_hits = 0

    for row_index, row in df.iterrows():
        excel_row = row_index + 2
        uid_value = row.get(resolved_columns["uid"])
        if is_blank(uid_value):
            continue

        try:
            uid = parse_int(uid_value, "编号")
        except ValueError as exc:
            record_validation_issue(summary, "invalid_uid", f"Excel 行 {excel_row}: {exc}", row=excel_row, raw_uid=clean_string(uid_value))
            summary.skipped += 1
            continue

        if uid in seen_uids:
            record_validation_issue(summary, "duplicate_uid", f"Excel 行 {excel_row}: UID 重复 {uid}", row=excel_row, uid=uid)
            summary.skipped += 1
            continue
        seen_uids.add(uid)

        name = clean_string(row.get(resolved_columns["name"]))
        if not name:
            record_validation_issue(summary, "missing_name", f"Excel 行 {excel_row}: UID {uid} 缺少姓名", row=excel_row, uid=uid)
            summary.skipped += 1
            continue

        try:
            age = parse_int(row.get(resolved_columns["age"]), "年龄")
            current_ca = parse_int(row.get(resolved_columns["ca"]), "当前CA")
            pa = parse_int(row.get(resolved_columns["pa"]), "PA")
        except ValueError as exc:
            record_validation_issue(summary, "invalid_numeric", f"Excel 行 {excel_row}: UID {uid} {exc}", row=excel_row, uid=uid, name=name)
            summary.skipped += 1
            continue

        initial_ca_column = resolved_columns.get("initial_ca")
        initial_ca = parse_optional_int(row.get(initial_ca_column), default=current_ca) if initial_ca_column else current_ca
        override = player_team_overrides.get(uid, {})
        raw_position = clean_string(row.get(resolved_columns["position"]))
        raw_team_name = clean_string(row.get(resolved_columns["team_name"]))
        club_team_name = clean_string(row.get(club_team_name_column)) if club_team_name_column else ""

        if strict_mode:
            position = raw_position
            team_name = raw_team_name
        else:
            position = clean_string(override.get("position")) or raw_position
            raw_team_name = clean_string(override.get("team_name")) or raw_team_name
            team_name = resolve_team_name(raw_team_name, teams_by_name, normalized_team_names)
            if team_name not in teams_by_name and club_team_name:
                fallback_team_name = resolve_team_name(club_team_name, teams_by_name, normalized_team_names)
                if fallback_team_name in teams_by_name:
                    team_name = fallback_team_name
                    club_team_fallback_hits += 1

        if not position:
            record_validation_issue(
                summary,
                "missing_position",
                f"Excel 行 {excel_row}: UID {uid} 缺少位置",
                row=excel_row,
                uid=uid,
                name=name,
                provided_team_name=raw_team_name,
            )
            summary.skipped += 1
            continue
        if not team_name:
            record_validation_issue(
                summary,
                "missing_team",
                f"Excel 行 {excel_row}: UID {uid} 缺少球队",
                row=excel_row,
                uid=uid,
                name=name,
            )
            summary.skipped += 1
            continue

        team = teams_by_name.get(team_name)
        if team is None:
            record_validation_issue(
                summary,
                "team_name_mismatch" if strict_mode else "unknown_team",
                f"Excel 行 {excel_row}: UID {uid} 的球队不存在: {team_name}",
                row=excel_row,
                uid=uid,
                name=name,
                provided_team_name=raw_team_name,
                club_team_name=club_team_name,
                normalized_team_name=team_name,
            )
            summary.skipped += 1
            continue
        if team_name != raw_team_name:
            alias_team_hits += 1

        player = existing_players.get(uid)
        is_new = player is None
        if player is None:
            player = Player(uid=uid)
            db.add(player)
            existing_players[uid] = player

        old_wage = player.wage
        old_slot_type = player.slot_type
        field_values = {
            "name": name,
            "age": age,
            "initial_ca": initial_ca,
            "ca": current_ca,
            "pa": pa,
            "position": position,
            "nationality": clean_string(row.get(resolved_columns["nationality"])),
            "team_id": team.id,
            "team_name": team_name,
        }
        changed = apply_model_updates(player, field_values)
        refresh_player_financials(player, db)
        if player.wage is None:
            player.wage = 0.0

        financial_changed = player.wage != old_wage or player.slot_type != old_slot_type
        if is_new:
            summary.created += 1
        elif changed or financial_changed:
            summary.updated += 1
        else:
            summary.unchanged += 1

    db.flush()
    if alias_team_hits:
        summary.details["team_alias_hits"] = alias_team_hits
    if club_team_fallback_hits:
        summary.details["club_team_fallback_hits"] = club_team_fallback_hits
    if strict_mode and "error_counts" in summary.details:
        summary.details["strict_mode_guidance"] = {
            "position_rule": "联赛名单.位置 必须非空",
            "team_rule": "联赛名单中的球队名必须与 信息总览.球队名 完全一致",
        }


def import_player_attributes(db: Session, attributes_csv_path: Path, report: ImportReport) -> None:
    summary = dataset_summary(report, "player_attributes", attributes_csv_path)
    try:
        df = pd.read_csv(attributes_csv_path, dtype=object, low_memory=False)
    except Exception as exc:
        summary.add_error(f"读取球员属性 CSV 失败: {exc}")
        return

    try:
        resolved_columns = {
            field_name: resolve_column(df, aliases, required=field_name in {"uid", "name"})
            for field_name, aliases in ATTRIBUTE_COLUMN_ALIASES.items()
        }
    except KeyError as exc:
        summary.add_error(str(exc))
        return

    existing_attributes = {record.uid: record for record in db.query(PlayerAttribute).all()}
    seen_uids: set[int] = set()

    for row_index, row in df.iterrows():
        csv_row = row_index + 2
        uid_value = row.get(resolved_columns["uid"])
        if is_blank(uid_value):
            continue
        try:
            uid = parse_int(uid_value, "UID")
        except ValueError as exc:
            summary.add_error(f"CSV 行 {csv_row}: {exc}")
            summary.skipped += 1
            continue

        if uid in seen_uids:
            summary.add_error(f"CSV 行 {csv_row}: UID 重复 {uid}")
            summary.skipped += 1
            continue
        seen_uids.add(uid)

        record = existing_attributes.get(uid)
        is_new = record is None
        if record is None:
            record = PlayerAttribute(uid=uid)
            db.add(record)
            existing_attributes[uid] = record

        field_values: dict[str, Any] = {"uid": uid}
        for field_name, column_name in resolved_columns.items():
            if field_name == "uid" or column_name is None:
                continue
            raw_value = row.get(column_name)
            if field_name in {"name", "position", "nationality", "club", "birth_date", "player_habits"}:
                field_values[field_name] = clean_string(raw_value)
            else:
                field_values[field_name] = parse_optional_int(raw_value, default=0)

        if not field_values.get("name"):
            summary.add_error(f"CSV 行 {csv_row}: UID {uid} 缺少姓名")
            summary.skipped += 1
            if is_new:
                db.expunge(record)
                existing_attributes.pop(uid, None)
            continue

        changed = apply_model_updates(record, field_values)
        if is_new:
            summary.created += 1
        elif changed:
            summary.updated += 1
        else:
            summary.unchanged += 1

    db.flush()


def seed_default_admin(db: Session, report: ImportReport, username: str, password: str) -> None:
    summary = dataset_summary(report, "admin_seed", Path("<runtime>"))
    existing = db.query(AdminUser).filter(AdminUser.username == username).first()
    if existing is None:
        db.add(AdminUser(username=username, password_hash=hash_password(password)))
        summary.created = 1
    else:
        summary.unchanged = 1
    db.flush()


def rebuild_team_caches(db: Session, report: ImportReport) -> None:
    summary = dataset_summary(report, "team_cache_rebuild", Path("<derived>"))
    recalculate_team_stats(
        db,
        commit=False,
        stat_scopes=PERSISTED_TEAM_STAT_SCOPES,
        refresh_mode=TEAM_CACHE_REFRESH_MODE_FULL_RECALC,
    )
    visible_team_count = db.query(Team).filter(Team.level != HIDDEN_SEA_TEAM_LEVEL).count()
    summary.updated = visible_team_count
    summary.details["refresh_mode"] = TEAM_CACHE_REFRESH_MODE_FULL_RECALC
    summary.details["growth_age_limit"] = get_growth_age_limit(db)


def run_import(
    workbook_path: str | Path | None = None,
    attributes_csv_path: str | Path | None = None,
    *,
    dry_run: bool = False,
    target_engine=None,
    root_dir: str | Path | None = None,
    seed_admin: bool = False,
    admin_username: str = "admin",
    admin_password: str = "heigo85",
    strict_mode: bool = True,
) -> ImportReport:
    active_engine = target_engine or engine
    init_database(target_engine=active_engine)

    workspace_root = Path(root_dir) if root_dir else Path(__file__).resolve().parent
    resolved_workbook, resolved_attributes_csv, warnings = resolve_input_files(workbook_path, attributes_csv_path, workspace_root)
    report = ImportReport(
        workbook_path=str(resolved_workbook),
        attributes_csv_path=str(resolved_attributes_csv),
        dry_run=dry_run,
        strict_mode=strict_mode,
        warnings=warnings,
    )

    session_factory = sessionmaker(bind=active_engine, autocommit=False, autoflush=False)
    db = session_factory()
    try:
        import_league_info(db, resolved_workbook, report)
        source_team_names = import_teams(db, resolved_workbook, report)
        import_players(db, resolved_workbook, report, strict_mode=strict_mode)
        import_player_attributes(db, resolved_attributes_csv, report)
        cleanup_stale_visible_teams(db, source_team_names, report)

        if seed_admin:
            seed_default_admin(db, report, admin_username, admin_password)

        if not report.has_errors:
            rebuild_team_caches(db, report)

        if report.has_errors:
            db.rollback()
        elif dry_run:
            db.rollback()
        else:
            db.commit()
            report.committed = True
    except Exception as exc:
        db.rollback()
        report.fatal_error = str(exc)
    finally:
        db.close()

    return report


def print_report(report: ImportReport) -> None:
    print("== HEIGO Import Report ==")
    print(f"workbook: {report.workbook_path}")
    print(f"attributes_csv: {report.attributes_csv_path}")
    print(f"dry_run: {report.dry_run}")
    print(f"strict_mode: {report.strict_mode}")
    print(f"committed: {report.committed}")
    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"- {warning}")

    for dataset_name, summary in report.datasets.items():
        print(f"\n[{dataset_name}]")
        print(
            f"created={summary.created} updated={summary.updated} unchanged={summary.unchanged} skipped={summary.skipped}"
        )
        for warning in summary.warnings:
            print(f"- warning: {warning}")
        for error in summary.errors:
            print(f"- error: {error}")
        if summary.details.get("error_counts"):
            print(f"- validation_error_counts: {json.dumps(summary.details['error_counts'], ensure_ascii=False)}")
        if summary.details:
            print(f"- details: {json.dumps(summary.details, ensure_ascii=False)}")

    if report.fatal_error:
        print(f"\nFatal error: {report.fatal_error}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HEIGO 联机联赛数据库导入工具")
    parser.add_argument("--workbook", type=str, help="联机联赛 Excel 文件路径")
    parser.add_argument("--attributes-csv", type=str, help="球员属性 CSV 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="只校验和预演导入，不提交数据库变更")
    parser.add_argument("--report-json", type=str, help="将导入报告输出到 JSON 文件")
    parser.add_argument("--seed-admin", action="store_true", help="额外创建 legacy admin 账户（默认不启用）")
    parser.add_argument("--admin-username", type=str, default="admin", help="legacy admin 用户名")
    parser.add_argument("--admin-password", type=str, default="heigo85", help="legacy admin 密码")
    parser.add_argument("--allow-legacy-fallback", action="store_true", help="允许使用球员对应球队、队名别名和俱乐部回退等兼容导入逻辑")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    report = run_import(
        workbook_path=args.workbook,
        attributes_csv_path=args.attributes_csv,
        dry_run=args.dry_run,
        seed_admin=args.seed_admin,
        admin_username=args.admin_username,
        admin_password=args.admin_password,
        strict_mode=not args.allow_legacy_fallback,
    )
    print_report(report)

    if args.report_json:
        report_path = Path(args.report_json)
        report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON report written to: {report_path}")

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
