from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

FACTOR_KEYS: Tuple[str, ...] = (
    "margin_of_safety",
    "quality",
    "growth",
    "momentum",
    "catalyst",
    "risk_control",
)

FACTOR_LABELS = {
    "margin_of_safety": "安全边际",
    "quality": "质量",
    "growth": "成长",
    "momentum": "趋势",
    "catalyst": "催化",
    "risk_control": "风控",
}


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp01(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_opportunities(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return [row for row in reader]


def normalize_weights(weights: Dict[str, Any]) -> Dict[str, float]:
    normalized: Dict[str, float] = {key: 0.0 for key in FACTOR_KEYS}
    total = 0.0
    for key in FACTOR_KEYS:
        weight = max(0.0, parse_float(weights.get(key, 0.0)))
        normalized[key] = weight
        total += weight

    if total == 0:
        even = 1.0 / len(FACTOR_KEYS)
        return {key: even for key in FACTOR_KEYS}

    return {key: value / total for key, value in normalized.items()}


def compute_factors(row: Dict[str, Any]) -> Dict[str, float]:
    price_to_fair_value = parse_float(row.get("price_to_fair_value"), 1.0)
    quality_score = parse_float(row.get("quality_score"), 0.0)
    growth_score = parse_float(row.get("growth_score"), 0.0)
    momentum_score = parse_float(row.get("momentum_score"), 0.0)
    catalyst_score = parse_float(row.get("catalyst_score"), 0.0)
    risk_score = parse_float(row.get("risk_score"), 100.0)

    # Keep signed MOS so overvaluation can be expressed as negative values.
    margin_of_safety = 1.0 - price_to_fair_value
    return {
        "margin_of_safety": margin_of_safety,
        "quality": clamp01(quality_score / 100.0),
        "growth": clamp01(growth_score / 100.0),
        "momentum": clamp01(momentum_score / 100.0),
        "catalyst": clamp01(catalyst_score / 100.0),
        "risk_control": clamp01(1.0 - (risk_score / 100.0)),
    }


def score_opportunity(
    row: Dict[str, Any], strategy_weights: Dict[str, Any]
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    factors = compute_factors(row)
    normalized_weights = normalize_weights(strategy_weights)

    contributions: Dict[str, float] = {}
    score = 0.0
    for key in FACTOR_KEYS:
        contribution = factors[key] * normalized_weights[key]
        contributions[key] = contribution
        score += contribution

    return score * 100.0, factors, contributions


def top_reasons(contributions: Dict[str, float], top_n: int = 3) -> List[str]:
    ordered = sorted(contributions.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [f"{FACTOR_LABELS[key]}:{value * 100:.1f}" for key, value in ordered]


def rank_opportunities(
    opportunities: Iterable[Dict[str, Any]],
    strategy: Dict[str, Any],
    top_n: int = 10,
    min_score: float = 0.0,
) -> List[Dict[str, Any]]:
    strategy_weights = strategy.get("weights", {})
    ranked: List[Dict[str, Any]] = []

    for row in opportunities:
        score, factors, contributions = score_opportunity(row, strategy_weights)
        if score < min_score:
            continue

        item = dict(row)
        item["score"] = round(score, 2)
        item["reason"] = " | ".join(top_reasons(contributions))
        item["margin_of_safety"] = round(factors["margin_of_safety"] * 100, 1)
        item["risk_control"] = round(factors["risk_control"] * 100, 1)
        ranked.append(item)

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_n]
