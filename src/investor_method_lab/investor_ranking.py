from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

METRIC_KEYS: Tuple[str, ...] = ("performance", "risk_control", "longevity", "transparency")
METRIC_LABELS = {
    "performance": "业绩",
    "risk_control": "风控",
    "longevity": "周期",
    "transparency": "透明度",
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


def normalize_metric_weights(weights: Dict[str, Any]) -> Dict[str, float]:
    normalized = {key: max(0.0, parse_float(weights.get(key, 0.0))) for key in METRIC_KEYS}
    total = sum(normalized.values())
    if total == 0:
        even = 1.0 / len(METRIC_KEYS)
        return {key: even for key in METRIC_KEYS}
    return {key: value / total for key, value in normalized.items()}


def score_investor(
    investor: Dict[str, Any], metric_weights: Dict[str, Any]
) -> Tuple[float, Dict[str, float]]:
    weights = normalize_metric_weights(metric_weights)
    metrics = investor.get("metrics", {})

    contributions: Dict[str, float] = {}
    score = 0.0
    for key in METRIC_KEYS:
        metric = clamp01(parse_float(metrics.get(key), 0.0) / 100.0)
        contribution = metric * weights[key]
        contributions[key] = contribution
        score += contribution

    return score * 100.0, contributions


def top_reason(contributions: Dict[str, float]) -> str:
    key, value = max(contributions.items(), key=lambda item: item[1])
    return f"{METRIC_LABELS[key]}:{value * 100:.1f}"


def rank_investors(
    investors: Iterable[Dict[str, Any]],
    metric_weights: Dict[str, Any],
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for investor in investors:
        score, contributions = score_investor(investor, metric_weights)
        item = dict(investor)
        item["score"] = round(score, 2)
        item["reason"] = top_reason(contributions)
        ranked.append(item)

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_n]
