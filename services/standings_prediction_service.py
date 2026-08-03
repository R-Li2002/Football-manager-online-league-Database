from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import math
import random
from threading import Lock
import time
from typing import Any


PREDICTION_SIMULATIONS = 1200
PREDICTION_INTERVAL_LABEL = "90%预测区间"
PREDICTION_CACHE_TTL_SECONDS = 90
_CACHE_LOCK = Lock()
_PREDICTION_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _percentile(sorted_values: list[int], fraction: float) -> int:
    if not sorted_values:
        return 0
    index = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * fraction)))
    return int(sorted_values[index])


def _phase(progress: float, remaining_match_count: int) -> tuple[str, str]:
    if remaining_match_count <= 0:
        return "final", "赛季已定"
    if progress < 0.25:
        return "early", "赛季初段"
    if progress < 0.6:
        return "middle", "赛季中段"
    if progress < 0.85:
        return "late", "赛季后段"
    return "run_in", "收官冲刺"


def _prediction_label(
    *,
    level: str,
    champion_probability: float,
    title_race_probability: float,
    promotion_probability: float,
    relegation_probability: float,
) -> str:
    if champion_probability >= 0.35:
        return "冠军热门"
    if title_race_probability >= 0.3:
        return "争冠集团"
    if level != "超级" and promotion_probability >= 0.45:
        return "升级竞争"
    if relegation_probability >= 0.45:
        return "保级压力"
    return "排名观察"


def _cache_get(key: str) -> dict[str, Any] | None:
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _PREDICTION_CACHE.get(key)
        if not cached:
            return None
        created_at, value = cached
        if now - created_at > PREDICTION_CACHE_TTL_SECONDS:
            _PREDICTION_CACHE.pop(key, None)
            return None
        return value


def _cache_set(key: str, value: dict[str, Any]) -> None:
    with _CACHE_LOCK:
        if len(_PREDICTION_CACHE) >= 24:
            oldest_key = min(_PREDICTION_CACHE, key=lambda item: _PREDICTION_CACHE[item][0])
            _PREDICTION_CACHE.pop(oldest_key, None)
        _PREDICTION_CACHE[key] = (time.monotonic(), value)


def _fingerprint(
    rows: list[dict[str, Any]],
    remaining_fixtures: list[tuple[str, str]],
    total_match_count: int,
) -> str:
    row_parts = [
        (
            str(row.get("team_name") or ""),
            int(row.get("played") or 0),
            int(row.get("points") or 0),
            int(row.get("goal_difference") or 0),
            int(row.get("goals_for") or 0),
            int(row.get("wins") or 0),
            int(row.get("home_played") or 0),
            int(row.get("home_points") or 0),
            int(row.get("away_played") or 0),
            int(row.get("away_points") or 0),
        )
        for row in sorted(rows, key=lambda item: str(item.get("team_name") or ""))
    ]
    payload = repr((row_parts, sorted(remaining_fixtures), int(total_match_count)))
    return sha256(payload.encode("utf-8")).hexdigest()


def _team_strengths(rows: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    # Six neutral prior matches stop one early upset from becoming a season-long certainty.
    prior_games = 6.0
    prior_ppg = 1.35
    overall: dict[str, float] = {}
    home_form: dict[str, float] = {}
    away_form: dict[str, float] = {}
    for row in rows:
        team_name = str(row.get("team_name") or "")
        played = float(row.get("played") or 0)
        points = float(row.get("points") or 0)
        goal_difference = float(row.get("goal_difference") or 0)
        ppg = (points + prior_games * prior_ppg) / (played + prior_games)
        gd_per_game = goal_difference / max(played + 3.0, 3.0)
        overall[team_name] = (ppg - prior_ppg) / 1.15 + gd_per_game * 0.28

        home_played = float(row.get("home_played") or 0)
        away_played = float(row.get("away_played") or 0)
        home_ppg = (float(row.get("home_points") or 0) + 3.0 * 1.48) / (home_played + 3.0)
        away_ppg = (float(row.get("away_points") or 0) + 3.0 * 1.22) / (away_played + 3.0)
        home_form[team_name] = (home_ppg - 1.48) / 1.4
        away_form[team_name] = (away_ppg - 1.22) / 1.4
    return overall, home_form, away_form


def _simulate_score(rng: random.Random, home_advantage: float) -> tuple[int, int]:
    draw_probability = max(0.17, 0.29 - min(0.1, abs(home_advantage) * 0.045))
    home_share = 1.0 / (1.0 + math.exp(-home_advantage * 1.28))
    home_win_probability = (1.0 - draw_probability) * home_share
    roll = rng.random()
    if roll < home_win_probability:
        margin_roll = rng.random()
        margin = 1 if margin_roll < 0.66 else 2 if margin_roll < 0.9 else 3
        loser_goals = 0 if rng.random() < 0.48 else 1 if rng.random() < 0.84 else 2
        return loser_goals + margin, loser_goals
    if roll < home_win_probability + draw_probability:
        draw_roll = rng.random()
        goals = 0 if draw_roll < 0.28 else 1 if draw_roll < 0.76 else 2
        return goals, goals
    margin_roll = rng.random()
    margin = 1 if margin_roll < 0.66 else 2 if margin_roll < 0.9 else 3
    loser_goals = 0 if rng.random() < 0.48 else 1 if rng.random() < 0.84 else 2
    return loser_goals, loser_goals + margin


def _empty_schedule_predictions(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    team_count = len(rows)
    uniform_champion = 1.0 / team_count if team_count else 0.0
    uniform_title = min(1.0, 2.0 / team_count) if team_count else 0.0
    uniform_zone = min(1.0, 5.0 / team_count) if team_count else 0.0
    return {
        str(row.get("team_name") or ""): {
            "predicted_rank": int(row.get("rank") or 0),
            "predicted_rank_min": 1 if team_count else 0,
            "predicted_rank_max": team_count,
            "prediction_confidence": 0.0,
            "champion_probability": round(uniform_champion, 4),
            "title_race_probability": round(uniform_title, 4),
            "promotion_probability": round(uniform_zone, 4),
            "relegation_probability": round(uniform_zone, 4),
            "prediction_label": "赛程待导入",
        }
        for row in rows
    }


def predict_level(
    level: str,
    rows: list[dict[str, Any]],
    remaining_fixtures: list[tuple[str, str]],
    *,
    total_match_count: int,
) -> dict[str, Any]:
    team_count = len(rows)
    played_match_count = max(0, int(total_match_count) - len(remaining_fixtures))
    progress = played_match_count / total_match_count if total_match_count else 0.0
    phase, phase_label = _phase(progress, len(remaining_fixtures)) if total_match_count else ("early", "赛程待导入")
    summary = {
        "level": level,
        "phase": phase,
        "phase_label": phase_label,
        "progress": round(progress, 4),
        "played_match_count": played_match_count,
        "remaining_match_count": len(remaining_fixtures),
        "total_match_count": int(total_match_count),
        "simulations": PREDICTION_SIMULATIONS if total_match_count else 0,
        "interval_label": PREDICTION_INTERVAL_LABEL,
    }
    if not rows:
        return {"summary": summary, "teams": {}}
    if total_match_count <= 0:
        return {"summary": summary, "teams": _empty_schedule_predictions(rows)}

    if not remaining_fixtures:
        predictions = {}
        for row in rows:
            rank = int(row.get("rank") or 0)
            predictions[str(row.get("team_name") or "")] = {
                "predicted_rank": rank,
                "predicted_rank_min": rank,
                "predicted_rank_max": rank,
                "prediction_confidence": 1.0,
                "champion_probability": 1.0 if rank == 1 else 0.0,
                "title_race_probability": 1.0 if rank <= 2 else 0.0,
                "promotion_probability": 1.0 if rank <= 5 else 0.0,
                "relegation_probability": 1.0 if rank > max(0, team_count - 5) else 0.0,
                "prediction_label": "最终排名",
            }
        return {"summary": summary, "teams": predictions}

    cache_key = f"{level}:{_fingerprint(rows, remaining_fixtures, total_match_count)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    team_names = [str(row.get("team_name") or "") for row in rows]
    row_by_name = {str(row.get("team_name") or ""): row for row in rows}
    overall, home_form, away_form = _team_strengths(rows)
    ranks_by_team: dict[str, list[int]] = defaultdict(list)
    seed = int(cache_key.split(":", 1)[1][:16], 16)
    rng = random.Random(seed)

    for _simulation in range(PREDICTION_SIMULATIONS):
        state = {
            team_name: {
                "points": int(row_by_name[team_name].get("points") or 0),
                "goal_difference": int(row_by_name[team_name].get("goal_difference") or 0),
                "goals_for": int(row_by_name[team_name].get("goals_for") or 0),
                "wins": int(row_by_name[team_name].get("wins") or 0),
            }
            for team_name in team_names
        }
        for home_team, away_team in remaining_fixtures:
            if home_team not in state or away_team not in state:
                continue
            advantage = (
                overall.get(home_team, 0.0)
                - overall.get(away_team, 0.0)
                + 0.18
                + 0.16 * home_form.get(home_team, 0.0)
                - 0.16 * away_form.get(away_team, 0.0)
            )
            home_score, away_score = _simulate_score(rng, advantage)
            home = state[home_team]
            away = state[away_team]
            home["goals_for"] += home_score
            away["goals_for"] += away_score
            home["goal_difference"] += home_score - away_score
            away["goal_difference"] += away_score - home_score
            if home_score > away_score:
                home["points"] += 3
                home["wins"] += 1
            elif away_score > home_score:
                away["points"] += 3
                away["wins"] += 1
            else:
                home["points"] += 1
                away["points"] += 1

        ranked = sorted(
            team_names,
            key=lambda name: (
                -state[name]["points"],
                -state[name]["goal_difference"],
                -state[name]["goals_for"],
                -state[name]["wins"],
                name,
            ),
        )
        for rank, team_name in enumerate(ranked, start=1):
            ranks_by_team[team_name].append(rank)

    predictions: dict[str, dict[str, Any]] = {}
    relegation_start = max(1, team_count - 4)
    for team_name in team_names:
        ranks = sorted(ranks_by_team[team_name])
        predicted_rank = max(1, min(team_count, round(sum(ranks) / len(ranks))))
        minimum = _percentile(ranks, 0.05)
        maximum = _percentile(ranks, 0.95)
        width = max(0, maximum - minimum)
        confidence = 1.0 if team_count <= 1 else max(0.0, 1.0 - width / (team_count - 1))
        champion_probability = sum(rank == 1 for rank in ranks) / len(ranks)
        title_race_probability = sum(rank <= 2 for rank in ranks) / len(ranks)
        promotion_probability = sum(rank <= min(5, team_count) for rank in ranks) / len(ranks)
        relegation_probability = sum(rank >= relegation_start for rank in ranks) / len(ranks)
        predictions[team_name] = {
            "predicted_rank": predicted_rank,
            "predicted_rank_min": minimum,
            "predicted_rank_max": maximum,
            "prediction_confidence": round(confidence, 4),
            "champion_probability": round(champion_probability, 4),
            "title_race_probability": round(title_race_probability, 4),
            "promotion_probability": round(promotion_probability, 4),
            "relegation_probability": round(relegation_probability, 4),
            "prediction_label": _prediction_label(
                level=level,
                champion_probability=champion_probability,
                title_race_probability=title_race_probability,
                promotion_probability=promotion_probability,
                relegation_probability=relegation_probability,
            ),
        }

    result = {"summary": summary, "teams": predictions}
    _cache_set(cache_key, result)
    return result
