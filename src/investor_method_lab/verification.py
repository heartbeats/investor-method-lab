from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

CONFIDENCE_ORDER: Dict[str, int] = {"A": 3, "B": 2, "C": 1}

METHODOLOGY_BUCKET_BY_ID: Dict[str, str] = {
    "peter_brandt": "趋势交易",
    "joel_greenblatt": "系统化价值",
    "james_simons": "量化统计套利",
    "george_soros": "全球宏观/反身性",
    "stanley_druckenmiller": "宏观+趋势",
    "michael_steinhardt": "宏观/事件驱动交易",
    "steven_cohen": "股票多空",
    "peter_lynch": "GARP 成长",
    "leon_levy": "套利/事件驱动",
    "paul_tudor_jones": "宏观趋势交易",
    "mohnish_pabrai": "深度价值",
    "shelby_davis": "行业价值",
    "bruce_kovner": "宏观 CTA",
    "warren_buffett": "价值质量复利",
    "howard_marks": "信用周期",
    "charlie_munger": "价值质量复利",
    "seth_klarman": "绝对收益价值",
    "bill_ackman": "激进主义投资",
    "walter_schloss": "深度价值分散",
    "dan_loeb": "事件驱动",
}


def confidence_value(level: str) -> int:
    return CONFIDENCE_ORDER.get(level.upper().strip(), 0)


def normalize_investor(investor: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(investor)
    item["confidence"] = str(item.get("confidence", "")).upper().strip()
    item["methodology_bucket"] = METHODOLOGY_BUCKET_BY_ID.get(
        item.get("id", ""), item.get("style", "未分类")
    )
    return item


def sort_for_ranking(investors: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        investors,
        key=lambda x: float(x.get("calibrated_return_pct", 0.0)),
        reverse=True,
    )


@dataclass
class VerificationResult:
    included: List[Dict[str, Any]]
    excluded: List[Dict[str, Any]]


def build_verified_universe(
    investors: Iterable[Dict[str, Any]], min_confidence: str = "B"
) -> VerificationResult:
    min_value = confidence_value(min_confidence)
    normalized = [normalize_investor(item) for item in investors]

    included = [item for item in normalized if confidence_value(item["confidence"]) >= min_value]
    excluded = [item for item in normalized if confidence_value(item["confidence"]) < min_value]

    ranked = sort_for_ranking(included)
    for index, item in enumerate(ranked, start=1):
        item["verified_rank"] = index

    excluded = sort_for_ranking(excluded)
    return VerificationResult(included=ranked, excluded=excluded)


def render_verified_markdown(
    included: List[Dict[str, Any]], min_confidence: str, as_of_date: str
) -> str:
    lines: List[str] = []
    lines.append(f"# 可审计投资人榜单（最小可信度 {min_confidence.upper()}）")
    lines.append("")
    lines.append(f"更新时间：{as_of_date}")
    lines.append("")
    lines.append(
        "| 排名 | 投资者 | 年化收益率 | 口径 | 统计区间 | 可信度 | 方法论分组 | 风格 |"
    )
    lines.append("|---|---|---:|---|---|---|---|---|")
    for item in included:
        name = f"{item.get('name_cn', '')} / {item.get('name_en', '')}"
        lines.append(
            f"| {item.get('verified_rank')} | {name} | {item.get('calibrated_return_pct')}% | "
            f"{item.get('return_basis', '')} | {item.get('period', '')} | {item.get('confidence', '')} | "
            f"{item.get('methodology_bucket', '')} | {item.get('style', '')} |"
        )

    return "\n".join(lines)


def render_backlog_markdown(excluded: List[Dict[str, Any]], min_confidence: str) -> str:
    lines: List[str] = []
    lines.append(f"# 待核验清单（低于 {min_confidence.upper()}）")
    lines.append("")
    lines.append("| 投资者 | 当前可信度 | 当前年化 | 口径 | 统计区间 | 核验建议 |")
    lines.append("|---|---|---:|---|---|---|")
    for item in excluded:
        name = f"{item.get('name_cn', '')} / {item.get('name_en', '')}"
        lines.append(
            f"| {name} | {item.get('confidence', '')} | {item.get('calibrated_return_pct')}% | "
            f"{item.get('return_basis', '')} | {item.get('period', '')} | 优先找官方信函/监管文件补证 |"
        )

    return "\n".join(lines)
