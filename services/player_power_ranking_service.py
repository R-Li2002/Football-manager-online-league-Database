from __future__ import annotations

import heapq
import json
import re
import time
from bisect import bisect_right
from dataclasses import dataclass
from statistics import median
from threading import Lock

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Player, Team, TeamLineup
from repositories.attribute_repository import iter_player_attributes, resolve_attribute_version
from repositories.player_repository import map_player_uid_to_team_name
from schemas_read import (
    PlayerPowerRankingItemResponse,
    PlayerPowerRankingResponse,
    TeamPowerSummariesResponse,
    TeamPowerSummaryItemResponse,
)
from services.share_card_model_service import build_preview_attributes
from weighted_power import calculate_weighted_power


POWER_GROWTH_CA_THRESHOLDS = {1: 11, 2: 30, 3: 50, 4: 70, 5: 90}
POWER_RANKING_SHAPES = {"all", "current", "1", "2", "3", "4", "5"}
TEAM_POWER_LEVELS = {"超级", "甲级", "乙级"}
FORMATION_SLOT_KEYS = {
    "4-3-3": ["gk", "def_l", "def_lc", "def_rc", "def_r", "mc_l", "mc_c", "mc_r", "am_wl", "fw_c", "am_wr"],
    "4-2-3-1": ["gk", "def_l", "def_lc", "def_rc", "def_r", "dm_l", "dm_r", "am_wl", "am_c", "am_wr", "fw_c"],
    "3-4-3": ["gk", "def_lc", "def_c", "def_rc", "mc_wl", "mc_l", "mc_r", "mc_wr", "fw_l", "fw_c", "fw_r"],
    "3-5-2": ["gk", "def_lc", "def_c", "def_rc", "dm_wl", "mc_l", "mc_c", "mc_r", "dm_wr", "fw_l", "fw_r"],
    "4-4-2": ["gk", "def_l", "def_lc", "def_rc", "def_r", "mc_wl", "mc_l", "mc_r", "mc_wr", "fw_l", "fw_r"],
}
TACTICAL_SLOT_ROLES = {
    "fw_l": ("ST", "AML", "LW"), "fw_c": ("ST", "CF"), "fw_r": ("ST", "AMR", "RW"),
    "am_wl": ("AML", "ML", "LW"), "am_l": ("AML", "AMC", "ST"), "am_c": ("AMC", "AM", "MC"),
    "am_r": ("AMR", "AMC", "ST"), "am_wr": ("AMR", "MR", "RW"),
    "mc_wl": ("ML", "AML", "LWB", "DL"), "mc_l": ("MC", "DM", "AMC"), "mc_c": ("MC", "DM"),
    "mc_r": ("MC", "DM", "AMC"), "mc_wr": ("MR", "AMR", "RWB", "DR"),
    "dm_wl": ("LWB", "WBL", "DL", "ML"), "dm_l": ("DM", "MC"), "dm_c": ("DM", "MC", "DC"),
    "dm_r": ("DM", "MC"), "dm_wr": ("RWB", "WBR", "DR", "MR"),
    "def_l": ("DL", "LWB", "WBL"), "def_lc": ("DC", "CB", "DL"), "def_c": ("DC", "CB"),
    "def_rc": ("DC", "CB", "DR"), "def_r": ("DR", "RWB", "WBR"), "gk": ("GK",),
}
POWER_CALIBRATION_CACHE_TTL_SECONDS = 300
TEAM_POWER_SUMMARY_CACHE_TTL_SECONDS = 600
_POWER_CACHE_LOCK = Lock()
_POWER_CALIBRATION_CACHE: dict[tuple[int, str], tuple[float, PowerCalibration]] = {}
_TEAM_POWER_SUMMARY_CACHE: dict[tuple[int, str], tuple[float, TeamPowerSummariesResponse]] = {}


@dataclass(frozen=True)
class PowerCalibration:
    data_version: str
    player_count: int
    median_score: float
    mad: float
    robust_scale: float
    sorted_scores: tuple[float, ...]


@dataclass(frozen=True)
class _RankingCandidate:
    uid: int
    name: str
    growth_step: int
    ca_gain: int
    ca: int
    projected_ca: int
    pa: int
    position: str
    weighted_power: float
    heigo_power: float
    top_percent: float
    heigo_club: str
    club: str


def _power_cache_key(db: Session, data_version: str) -> tuple[int, str]:
    try:
        namespace = id(db.get_bind())
    except (AttributeError, TypeError):
        namespace = id(db)
    return namespace, data_version


def invalidate_power_caches() -> None:
    with _POWER_CACHE_LOCK:
        _POWER_CALIBRATION_CACHE.clear()
        _TEAM_POWER_SUMMARY_CACHE.clear()


def _read_timed_cache(cache: dict, key: tuple[int, str], ttl_seconds: int):
    now = time.monotonic()
    with _POWER_CACHE_LOCK:
        cached = cache.get(key)
        if not cached:
            return None
        created_at, value = cached
        if now - created_at > ttl_seconds:
            cache.pop(key, None)
            return None
        return value


def _write_timed_cache(cache: dict, key: tuple[int, str], value) -> None:
    with _POWER_CACHE_LOCK:
        cache[key] = (time.monotonic(), value)


def eligible_growth_steps(ca: int, pa: int, shape: str = "all") -> list[tuple[int, int]]:
    gap = max(0, int(pa or 0) - int(ca or 0))
    candidates = [(0, 0)] + [
        (step, ca_gain)
        for step, ca_gain in POWER_GROWTH_CA_THRESHOLDS.items()
        if gap >= ca_gain
    ]
    if shape == "current":
        return candidates[:1]
    if shape != "all":
        requested_step = int(shape)
        return [item for item in candidates if item[0] == requested_step]
    return candidates


def _candidate_heap_key(candidate: _RankingCandidate) -> tuple[float, int, int, int]:
    return (
        candidate.weighted_power,
        -candidate.growth_step,
        candidate.ca,
        -candidate.uid,
    )


def get_power_calibration(db: Session, *, data_version: str | None = None) -> PowerCalibration:
    resolved_version = resolve_attribute_version(db, data_version)
    cache_key = _power_cache_key(db, resolved_version)
    cached = _read_timed_cache(_POWER_CALIBRATION_CACHE, cache_key, POWER_CALIBRATION_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    team_map = map_player_uid_to_team_name(db)
    eligible_uids = set(team_map)
    scores: list[float] = []
    for player in iter_player_attributes(db, data_version=resolved_version, player_uids=eligible_uids):
        if int(player.uid) not in eligible_uids or int(getattr(player, "pos_gk", 0) or 0) >= 15:
            continue
        score = calculate_weighted_power(player, precision=2).score
        if score is not None:
            scores.append(float(score))

    sorted_scores = tuple(sorted(scores))
    if not sorted_scores:
        calibration = PowerCalibration(resolved_version, 0, 0.0, 0.0, 1.0, ())
    else:
        median_score = float(median(sorted_scores))
        mad = float(median(abs(score - median_score) for score in sorted_scores))
        robust_scale = max(1.0, 1.4826 * mad)
        calibration = PowerCalibration(
            data_version=resolved_version,
            player_count=len(sorted_scores),
            median_score=round(median_score, 2),
            mad=round(mad, 4),
            robust_scale=round(robust_scale, 4),
            sorted_scores=sorted_scores,
        )
    _write_timed_cache(_POWER_CALIBRATION_CACHE, cache_key, calibration)
    return calibration


def calculate_heigo_metrics(weighted_power: float, calibration: PowerCalibration) -> tuple[float, float]:
    score = float(weighted_power)
    heigo_power = max(
        0.0,
        min(100.0, 50.0 + 10.0 * ((score - calibration.median_score) / calibration.robust_scale)),
    )
    if not calibration.player_count:
        return round(heigo_power, 2), 100.0
    stronger_players = calibration.player_count - bisect_right(calibration.sorted_scores, score)
    top_percent = ((stronger_players + 1) / calibration.player_count) * 100
    return round(heigo_power, 2), round(max(0.01, min(100.0, top_percent)), 2)


def get_player_power_ranking(
    db: Session,
    *,
    shape: str = "all",
    limit: int | str = 50,
    team_name: str | None = None,
    data_version: str | None = None,
) -> PlayerPowerRankingResponse:
    normalized_shape = str(shape or "all").strip().lower()
    if normalized_shape not in POWER_RANKING_SHAPES:
        raise HTTPException(status_code=400, detail="成长形态仅支持 all、current、1、2、3、4、5。")

    requested_limit = str(limit or "50").strip().lower()
    show_all = requested_limit == "all"
    if show_all:
        normalized_limit: int | str = "all"
    else:
        try:
            normalized_limit = max(1, min(100, int(requested_limit)))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="显示数量仅支持 1-100 或 all。") from exc
    resolved_version = resolve_attribute_version(db, data_version)
    calibration = get_power_calibration(db, data_version=resolved_version)
    team_map = map_player_uid_to_team_name(db)
    eligible_uids = {
        uid
        for uid, mapped_team in team_map.items()
        if not team_name or mapped_team == team_name
    }
    heap: list[tuple[tuple[float, int, int, int], int, _RankingCandidate]] = []
    all_entries: list[tuple[tuple[float, int, int, int], int, _RankingCandidate]] = []
    sequence = 0

    for player in iter_player_attributes(db, data_version=resolved_version, player_uids=eligible_uids):
        player_uid = int(player.uid)
        if player_uid not in eligible_uids:
            continue
        heigo_club = team_map[player_uid]
        if int(getattr(player, "pos_gk", 0) or 0) >= 15:
            continue

        ca = int(getattr(player, "ca", 0) or 0)
        pa = int(getattr(player, "pa", 0) or 0)
        for growth_step, ca_gain in eligible_growth_steps(ca, pa, normalized_shape):
            preview = build_preview_attributes(player, growth_step)
            power = calculate_weighted_power(preview, precision=2).score
            if power is None:
                continue
            heigo_power, top_percent = calculate_heigo_metrics(power, calibration)
            candidate = _RankingCandidate(
                uid=player_uid,
                name=str(getattr(player, "name", "") or ""),
                growth_step=growth_step,
                ca_gain=ca_gain,
                ca=ca,
                projected_ca=min(pa, ca + ca_gain),
                pa=pa,
                position=str(getattr(player, "position", "") or ""),
                weighted_power=power,
                heigo_power=heigo_power,
                top_percent=top_percent,
                heigo_club=heigo_club,
                club=str(getattr(player, "club", "") or ""),
            )
            entry = (_candidate_heap_key(candidate), sequence, candidate)
            sequence += 1
            if show_all:
                all_entries.append(entry)
                continue
            if len(heap) < normalized_limit:
                heapq.heappush(heap, entry)
            elif entry[0] > heap[0][0]:
                heapq.heapreplace(heap, entry)

    ranking_entries = all_entries if show_all else heap
    ordered = [entry[2] for entry in sorted(ranking_entries, key=lambda entry: entry[0], reverse=True)]
    return PlayerPowerRankingResponse(
        shape=normalized_shape,
        limit=normalized_limit,
        team=team_name or None,
        data_version=resolved_version,
        items=[
            PlayerPowerRankingItemResponse(
                rank=index,
                uid=item.uid,
                name=item.name,
                display_name=f"{item.name} +{item.growth_step}" if item.growth_step else item.name,
                growth_step=item.growth_step,
                ca_gain=item.ca_gain,
                ca=item.ca,
                projected_ca=item.projected_ca,
                pa=item.pa,
                potential_gap=max(0, item.pa - item.ca),
                position=item.position,
                weighted_power=item.weighted_power,
                heigo_power=item.heigo_power,
                top_percent=item.top_percent,
                heigo_club=item.heigo_club,
                club=item.club,
                data_version=resolved_version,
            )
            for index, item in enumerate(ordered, start=1)
        ],
    )


def _estimated_growth_step(player: Player) -> int:
    gain = max(0, int(player.ca or 0) - int(player.initial_ca or 0))
    for step, threshold in sorted(POWER_GROWTH_CA_THRESHOLDS.items(), reverse=True):
        if gain >= threshold:
            return step
    return 0


def _position_matches_role(position: str | None, raw_role: str) -> bool:
    role = str(raw_role or "").upper()
    normalized = re.sub(r"[(),\-/]+", " ", str(position or "").upper())
    tokens = {token for token in normalized.split() if token}
    compact = re.sub(r"[^A-Z0-9]", "", str(position or "").upper())
    if role in tokens or role in compact:
        return True
    aliases = {
        "CB": ("DC",), "DC": ("DC",),
        "DL": ("DL", "WBL"), "LWB": ("WBL", "DL"), "WBL": ("WBL", "DL"),
        "DR": ("DR", "WBR"), "RWB": ("WBR", "DR"), "WBR": ("WBR", "DR"),
        "CM": ("MC", "DM"), "MC": ("MC",), "DM": ("DM",),
        "AM": ("AMC",), "AMC": ("AMC",), "AML": ("AML", "ML"), "LW": ("AML", "ML"),
        "AMR": ("AMR", "MR"), "RW": ("AMR", "MR"), "ML": ("ML",), "MR": ("MR",),
        "ST": ("ST",), "CF": ("ST",), "GK": ("GK",),
    }
    return any(alias in tokens or alias in compact for alias in aliases.get(role, (role,)))


def _auto_lineup_uids(players: list[Player], formation: str) -> list[int]:
    ordered = sorted(players, key=lambda item: (-int(item.ca or 0), str(item.name or "")))
    used: set[int] = set()
    picks: list[int] = []
    for slot_key in FORMATION_SLOT_KEYS.get(formation, FORMATION_SLOT_KEYS["4-3-3"]):
        roles = TACTICAL_SLOT_ROLES.get(slot_key, ())
        candidate = next(
            (player for player in ordered if int(player.uid) not in used and any(_position_matches_role(player.position, role) for role in roles)),
            None,
        )
        if candidate is None:
            candidate = next((player for player in ordered if int(player.uid) not in used), None)
        if candidate is not None:
            used.add(int(candidate.uid))
            picks.append(int(candidate.uid))
    return picks


def _decode_lineup_uids(raw_value: str | None) -> list[int]:
    try:
        payload = json.loads(raw_value or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    return [int(uid) for uid in payload.values() if str(uid).isdigit() and int(uid) > 0]


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def get_team_power_summaries(db: Session, *, data_version: str | None = None) -> TeamPowerSummariesResponse:
    resolved_version = resolve_attribute_version(db, data_version)
    cache_key = _power_cache_key(db, resolved_version)
    cached = _read_timed_cache(_TEAM_POWER_SUMMARY_CACHE, cache_key, TEAM_POWER_SUMMARY_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached.model_copy(deep=True)
    teams = db.query(Team).filter(Team.level.in_(TEAM_POWER_LEVELS)).order_by(Team.level, Team.name).all()
    team_by_id = {int(team.id): team for team in teams}
    team_by_name = {str(team.name): team for team in teams}
    players = db.query(Player).all()
    players_by_team_id: dict[int, list[Player]] = {int(team.id): [] for team in teams}
    player_by_uid: dict[int, Player] = {}
    for player in players:
        team = team_by_id.get(int(player.team_id or 0)) or team_by_name.get(str(player.team_name or ""))
        if not team:
            continue
        players_by_team_id[int(team.id)].append(player)
        player_by_uid[int(player.uid)] = player

    calibration = get_power_calibration(db, data_version=resolved_version)
    power_by_uid: dict[int, float] = {}
    for attribute in iter_player_attributes(db, data_version=resolved_version, player_uids=player_by_uid):
        uid = int(attribute.uid)
        league_player = player_by_uid.get(uid)
        if not league_player or int(getattr(attribute, "pos_gk", 0) or 0) >= 15:
            continue
        requested_step = _estimated_growth_step(league_player)
        available_steps = {step for step, _ in eligible_growth_steps(int(attribute.ca or 0), int(attribute.pa or 0), "all")}
        applied_step = requested_step
        while applied_step > 0 and applied_step not in available_steps:
            applied_step -= 1
        preview = build_preview_attributes(attribute, applied_step)
        weighted_power = calculate_weighted_power(preview, precision=2).score
        if weighted_power is None:
            continue
        power_by_uid[uid] = calculate_heigo_metrics(float(weighted_power), calibration)[0]

    lineups = {int(item.team_id): item for item in db.query(TeamLineup).all()}
    rows: list[dict] = []
    for team in teams:
        team_players = players_by_team_id.get(int(team.id), [])
        roster_values = [power_by_uid[int(player.uid)] for player in team_players if int(player.uid) in power_by_uid]
        lineup = lineups.get(int(team.id))
        lineup_uids = _decode_lineup_uids(lineup.picks_json) if lineup else []
        if not lineup_uids:
            lineup_uids = _auto_lineup_uids(team_players, lineup.formation if lineup else "4-3-3")
        lineup_values = [power_by_uid[uid] for uid in lineup_uids if uid in power_by_uid]
        rows.append({
            "team": team,
            "roster_average": _average(roster_values),
            "roster_player_count": len(roster_values),
            "lineup_average": _average(lineup_values),
            "lineup_player_count": len(lineup_values),
        })

    for field in ("roster_average", "lineup_average"):
        rank_field = field.replace("average", "rank")
        for level in TEAM_POWER_LEVELS:
            level_rows = [row for row in rows if row["team"].level == level and row[field] is not None]
            level_rows.sort(key=lambda row: (-float(row[field]), str(row["team"].name)))
            for rank, row in enumerate(level_rows, start=1):
                row[rank_field] = rank

    response = TeamPowerSummariesResponse(
        data_version=resolved_version,
        items=[
            TeamPowerSummaryItemResponse(
                team_id=int(row["team"].id),
                team_name=str(row["team"].name),
                level=str(row["team"].level),
                roster_average=row["roster_average"],
                roster_rank=row.get("roster_rank"),
                roster_player_count=row["roster_player_count"],
                lineup_average=row["lineup_average"],
                lineup_rank=row.get("lineup_rank"),
                lineup_player_count=row["lineup_player_count"],
            )
            for row in rows
        ],
    )
    _write_timed_cache(_TEAM_POWER_SUMMARY_CACHE, cache_key, response)
    return response.model_copy(deep=True)
