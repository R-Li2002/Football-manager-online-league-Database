from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


WEIGHTED_POWER_WEIGHTS: dict[str, float] = {
    "passing": 0.347,
    "crossing": 0.182,
    "marking": 0.147,
    "penalty": 0.0,
    "technique": -0.071,
    "corner": 0.0,
    "long_throws": 0.0,
    "dribbling": 1.376,
    "tackling": 0.159,
    "free_kick": 0.0,
    "finishing": 0.682,
    "first_touch": 0.194,
    "heading": 0.271,
    "long_shots": 0.394,
    "flair": -0.012,
    "positioning": 0.494,
    "work_rate": 3.471,
    "concentration": 1.388,
    "decisions": 0.035,
    "leadership": 0.012,
    "aggression": 0.494,
    "vision": 0.253,
    "teamwork": 0.024,
    "off_the_ball": 0.094,
    "determination": 0.688,
    "bravery": -0.024,
    "anticipation": 1.059,
    "composure": 0.635,
    "acceleration": 5.669,
    "jumping": 1.647,
    "agility": 1.135,
    "stamina": 1.229,
    "balance": 1.206,
    "strength": 0.671,
    "pace": 5.654,
    "natural_fitness": 0.647,
    "consistency": 0.306,
    "important_matches": 0.335,
    "pressure": 1.594,
}

WEIGHTED_POWER_ACTIVE_WEIGHTS = tuple(
    (field, weight)
    for field, weight in WEIGHTED_POWER_WEIGHTS.items()
    if weight != 0
)


@dataclass(frozen=True)
class WeightedPowerResult:
    score: float | None
    raw_score: float | None
    included: int
    total: int
    is_goalkeeper: bool


def _read_value(source: Any, field: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(field)
    return getattr(source, field, None)


def calculate_weighted_power(source: Any, *, precision: int = 2) -> WeightedPowerResult:
    is_goalkeeper = float(_read_value(source, "pos_gk") or 0) >= 15
    if is_goalkeeper:
        return WeightedPowerResult(None, None, 0, len(WEIGHTED_POWER_ACTIVE_WEIGHTS), True)

    raw_score = 0.0
    theoretical_min = 0.0
    theoretical_max = 0.0
    included = 0

    for field, weight in WEIGHTED_POWER_ACTIVE_WEIGHTS:
        raw_value = _read_value(source, field)
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if numeric_value <= 0:
            continue
        value = max(1.0, min(20.0, numeric_value))
        raw_score += value * weight
        theoretical_min += weight if weight >= 0 else weight * 20
        theoretical_max += weight * 20 if weight >= 0 else weight
        included += 1

    score_range = theoretical_max - theoretical_min
    if not included or score_range <= 0:
        return WeightedPowerResult(None, None, included, len(WEIGHTED_POWER_ACTIVE_WEIGHTS), False)

    score = max(0.0, min(100.0, ((raw_score - theoretical_min) / score_range) * 100))
    normalized_precision = max(0, min(4, int(precision)))
    return WeightedPowerResult(round(score, normalized_precision), raw_score, included, len(WEIGHTED_POWER_ACTIVE_WEIGHTS), False)


def build_weighted_power_sql_expression(attribute_model):
    from sqlalchemy import and_, case, func

    raw_score = 0.0
    theoretical_min = 0.0
    theoretical_max = 0.0

    for field, weight in WEIGHTED_POWER_ACTIVE_WEIGHTS:
        column = getattr(attribute_model, field)
        clamped_value = case(
            (column < 1, 1.0),
            (column > 20, 20.0),
            else_=column,
        )
        available = column > 0
        raw_score += case((available, clamped_value * weight), else_=0.0)
        theoretical_min += case((available, weight if weight >= 0 else weight * 20), else_=0.0)
        theoretical_max += case((available, weight * 20 if weight >= 0 else weight), else_=0.0)

    score_range = theoretical_max - theoretical_min
    return case(
        (
            and_(func.coalesce(attribute_model.pos_gk, 0) < 15, score_range > 0),
            ((raw_score - theoretical_min) * 100.0) / score_range,
        ),
        else_=None,
    )
