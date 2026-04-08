from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from attribute_versions import infer_attribute_data_version
from auth_utils import hash_password
from database import engine, init_database
from imports_runtime.attribute_parser import load_player_attributes_source
from imports_runtime.constants import (
    ATTRIBUTE_COLUMN_ALIASES,
    DEFAULT_LEAGUE_INFO_VALUES,
    GK_COEFFICIENT_RE,
    HIDDEN_SEA_TEAM_LEVEL,
    HIDDEN_SEA_TEAM_MANAGER,
    HIDDEN_SEA_TEAM_NAME,
    PLAYER_COLUMN_ALIASES,
    SUPPORTED_INFO_KEY_ALIASES,
    TEAM_COLUMN_ALIASES,
    WORKBOOK_SHEET_LEAGUE_PLAYERS,
    WORKBOOK_SHEET_OVERVIEW,
)
from imports_runtime.reporting import ImportReport, dataset_summary
from imports_runtime.source_resolver import resolve_input_files
from imports_runtime.validators import (
    apply_model_updates,
    clean_string,
    is_blank,
    normalize_team_identifier,
    parse_int,
    parse_optional_float,
    parse_optional_int,
    record_validation_issue,
    resolve_column,
)
from imports_runtime.workbook_parser import load_excel, load_player_team_overrides, resolve_team_name
from league_settings import create_league_info_record, get_growth_age_limit
from models import AdminUser, LeagueInfo, Player, PlayerAttribute, PlayerAttributeVersion, Team, TransferLog
from services.league_service import (
    PERSISTED_TEAM_STAT_SCOPES,
    TEAM_CACHE_REFRESH_MODE_FULL_RECALC,
    recalculate_team_stats,
    refresh_player_financials,
)

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

def cleanup_stale_players(db: Session, source_player_uids: set[int] | None, report: ImportReport) -> set[str]:
    summary = dataset_summary(report, "player_sync_cleanup", Path("<derived>"))
    source_player_uids = source_player_uids or set()
    summary.details["source_uid_count"] = len(source_player_uids)
    if not source_player_uids:
        summary.add_warning("No source player UIDs were resolved; player full-sync cleanup skipped.")
        return set()

    stale_players = db.query(Player).filter(Player.uid.not_in(source_player_uids)).order_by(Player.uid.asc()).all()
    removed_team_counter: Counter[str] = Counter()
    removed_player_samples: list[dict[str, Any]] = []

    for player in stale_players:
        team_name = clean_string(player.team_name)
        if team_name:
            removed_team_counter[team_name] += 1
        if len(removed_player_samples) < 20:
            removed_player_samples.append(
                {
                    "uid": player.uid,
                    "name": clean_string(player.name),
                    "team_name": team_name,
                }
            )
        db.delete(player)

    summary.updated = len(stale_players)
    summary.details["candidate_count"] = len(stale_players)
    summary.details["removed_count"] = len(stale_players)
    if removed_team_counter:
        summary.details["removed_team_breakdown"] = dict(sorted(removed_team_counter.items()))
    if removed_player_samples:
        summary.details["removed_players_sample"] = removed_player_samples
    db.flush()
    return set(removed_team_counter)

def import_players(db: Session, workbook_path: Path, report: ImportReport, *, strict_mode: bool = True) -> set[int]:
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

    return seen_uids

def import_player_attributes(db: Session, attributes_csv_path: Path, report: ImportReport) -> None:
    summary = dataset_summary(report, "player_attributes", attributes_csv_path)
    data_version = infer_attribute_data_version(attributes_csv_path)
    summary.details["data_version"] = data_version
    try:
        df, source_metadata = load_player_attributes_source(attributes_csv_path)
    except Exception as exc:
        summary.add_error(f"读取球员属性文件失败: {exc}")
        return

    summary.details["source_format"] = source_metadata.get("source_format", "unknown")
    if source_metadata.get("encoding"):
        summary.details["encoding"] = source_metadata["encoding"]
    if source_metadata.get("sheet_name"):
        summary.details["sheet_name"] = source_metadata["sheet_name"]
    if source_metadata.get("header_row"):
        summary.details["header_row"] = source_metadata["header_row"]
    if source_metadata.get("renamed_headers"):
        summary.details["header_renames"] = source_metadata["renamed_headers"]
    if source_metadata.get("derived_columns"):
        summary.details["derived_columns"] = source_metadata["derived_columns"]
    if source_metadata.get("negative_pa_override_count"):
        summary.details["negative_pa_override_count"] = source_metadata["negative_pa_override_count"]
    for detail_key in (
        "player_habit_numeric_rows",
        "player_habit_decoded_rows",
        "player_habit_high_bits_rows",
        "player_habit_unresolved_rows",
    ):
        if detail_key in source_metadata:
            summary.details[detail_key] = source_metadata[detail_key]

    try:
        resolved_columns = {
            field_name: resolve_column(df, aliases, required=field_name in {"uid", "name"})
            for field_name, aliases in ATTRIBUTE_COLUMN_ALIASES.items()
        }
    except KeyError as exc:
        summary.add_error(str(exc))
        return

    existing_versioned_attributes = {
        (record.uid, record.data_version): record
        for record in db.query(PlayerAttributeVersion)
        .filter(PlayerAttributeVersion.data_version == data_version)
        .all()
    }
    existing_legacy_attributes = {record.uid: record for record in db.query(PlayerAttribute).all()}
    seen_uids: set[int] = set()
    legacy_cache_created = 0
    legacy_cache_updated = 0
    legacy_cache_unchanged = 0

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

        versioned_key = (uid, data_version)
        versioned_record = existing_versioned_attributes.get(versioned_key)
        is_new = versioned_record is None
        if versioned_record is None:
            versioned_record = PlayerAttributeVersion(uid=uid, data_version=data_version)
            db.add(versioned_record)
            existing_versioned_attributes[versioned_key] = versioned_record

        legacy_record = existing_legacy_attributes.get(uid)
        legacy_is_new = legacy_record is None
        if legacy_record is None:
            legacy_record = PlayerAttribute(uid=uid)
            db.add(legacy_record)
            existing_legacy_attributes[uid] = legacy_record

        field_values: dict[str, Any] = {"uid": uid}
        float_attribute_fields = {
            "radar_defense",
            "radar_physical",
            "radar_speed",
            "radar_creativity",
            "radar_attack",
            "radar_technical",
            "radar_aerial",
            "radar_mental",
            "radar_gk_shot_stopping",
            "radar_gk_physical",
            "radar_gk_speed",
            "radar_gk_mental",
            "radar_gk_command",
            "radar_gk_eccentricity",
            "radar_gk_aerial",
            "radar_gk_kicking",
        }
        for field_name, column_name in resolved_columns.items():
            if field_name == "uid" or column_name is None:
                continue
            raw_value = row.get(column_name)
            if field_name in {
                "name",
                "position",
                "nationality",
                "club",
                "birth_date",
                "player_habits",
                "player_habits_raw_code",
                "player_habits_high_bits",
            }:
                field_values[field_name] = clean_string(raw_value)
            elif field_name in float_attribute_fields:
                field_values[field_name] = parse_optional_float(raw_value, default=0.0)
            else:
                field_values[field_name] = parse_optional_int(raw_value, default=0)

        if not field_values.get("name"):
            summary.add_error(f"CSV 行 {csv_row}: UID {uid} 缺少姓名")
            summary.skipped += 1
            if is_new:
                db.expunge(versioned_record)
                existing_versioned_attributes.pop(versioned_key, None)
            if legacy_is_new:
                db.expunge(legacy_record)
                existing_legacy_attributes.pop(uid, None)
            continue

        versioned_field_values = dict(field_values)
        versioned_field_values["data_version"] = data_version
        changed = apply_model_updates(versioned_record, versioned_field_values)
        legacy_changed = apply_model_updates(legacy_record, field_values)
        if is_new:
            summary.created += 1
        elif changed:
            summary.updated += 1
        else:
            summary.unchanged += 1

        if legacy_is_new:
            legacy_cache_created += 1
        elif legacy_changed:
            legacy_cache_updated += 1
        else:
            legacy_cache_unchanged += 1

    summary.details["legacy_cache_created"] = legacy_cache_created
    summary.details["legacy_cache_updated"] = legacy_cache_updated
    summary.details["legacy_cache_unchanged"] = legacy_cache_unchanged
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

    configured_root = os.environ.get("HEIGO_IMPORT_ROOT")
    workspace_root = (
        Path(root_dir)
        if root_dir
        else Path(configured_root).expanduser().resolve()
        if configured_root
        else Path(__file__).resolve().parents[1]
    )
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
        source_player_uids = import_players(db, resolved_workbook, report, strict_mode=strict_mode)
        cleanup_stale_players(db, source_player_uids, report)
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
