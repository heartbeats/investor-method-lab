from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from investor_method_lab.opportunity_validation import valuation_support_tier
from investor_method_lab.review_writeback import reviewed_items, reviewed_items_by_ticker, summarize_review_writeback
from investor_method_lab.signal_ledger import (
    latest_entries_by_ticker,
    normalize_internal_symbol_for_ticker,
    normalize_text,
    read_json,
    ticker_lookup_keys,
)


def load_real_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows.append(dict(row))
    return rows


def load_focus_lookup(path: Path) -> set[str]:
    payload = read_json(path)
    symbols = payload.get("symbols") or []
    keys: set[str] = set()
    for item in symbols:
        if not isinstance(item, dict):
            continue
        for raw in [item.get("ticker"), item.get("dcf_symbol"), normalize_internal_symbol_for_ticker(item.get("ticker"))]:
            for key in ticker_lookup_keys(raw):
                keys.add(normalize_text(key).upper())
    return keys


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def row_lookup_keys(row: Dict[str, Any]) -> set[str]:
    values = [row.get("ticker"), row.get("dcf_symbol"), row.get("symbol")]
    keys: set[str] = set()
    for value in values:
        for key in ticker_lookup_keys(value):
            keys.add(normalize_text(key).upper())
    return keys


def support_counts(rows: Sequence[Dict[str, Any]], source_field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        support = valuation_support_tier(row.get(source_field))
        counts[support] = counts.get(support, 0) + 1
    return counts


def source_counts(rows: Sequence[Dict[str, Any]], source_field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        key = normalize_text(row.get(source_field)) or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


def pool_summary(rows: Sequence[Dict[str, Any]], source_field: str) -> Dict[str, Any]:
    total = len(rows)
    sources = source_counts(rows, source_field)
    supports = support_counts(rows, source_field)
    formal = supports.get("formal_core", 0) + supports.get("formal_support", 0)
    reference = supports.get("reference_only", 0)
    fallback = supports.get("price_fallback", 0)
    return {
        "count": total,
        "valuation_source_breakdown": sources,
        "valuation_support_breakdown": supports,
        "formal_valuation_coverage_rate": (formal / total) if total else None,
        "formal_or_reference_coverage_rate": ((formal + reference) / total) if total else None,
        "price_fallback_rate": (fallback / total) if total else None,
        "high_quality_formal_rate": (supports.get("formal_core", 0) / total) if total else None,
    }


def positions_by_signal_id(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {normalize_text(row.get("signal_id")): row for row in rows if isinstance(row, dict)}


def latest_signal_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list(latest_entries_by_ticker(rows).values())


def summarize_validation_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    evaluated = [row for row in rows if normalize_text(row.get("status")) != "pending_entry"]
    returns = [float(row.get("strategy_return_net")) for row in evaluated if row.get("strategy_return_net") is not None]
    excess = [float(row.get("primary_excess_return")) for row in evaluated if row.get("primary_excess_return") is not None]
    hits = [bool(row.get("hit")) for row in evaluated if row.get("hit") is not None]
    return {
        "count": len(rows),
        "evaluated_count": len(evaluated),
        "open_count": sum(1 for row in rows if normalize_text(row.get("status")) == "open"),
        "closed_count": sum(1 for row in rows if normalize_text(row.get("status")) == "closed"),
        "expired_count": sum(1 for row in rows if normalize_text(row.get("status")) == "expired"),
        "pending_entry_count": sum(1 for row in rows if normalize_text(row.get("status")) == "pending_entry"),
        "avg_strategy_return_net": (sum(returns) / len(returns)) if returns else None,
        "avg_primary_excess_return": (sum(excess) / len(excess)) if excess else None,
        "hit_rate": (sum(1 for item in hits if item) / len(hits)) if hits else None,
    }


def summarize_confidence_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        bucket = normalize_text(row.get("trust_bucket")) or "unknown"
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def quality_priority(support: str) -> int:
    return {
        "price_fallback": 0,
        "reference_only": 1,
        "unknown": 2,
        "formal_support": 3,
        "formal_core": 4,
    }.get(normalize_text(support), 9)


def build_gap_rows(
    *,
    real_focus_rows: Sequence[Dict[str, Any]],
    signal_rows: Sequence[Dict[str, Any]],
    confidence_rows: Sequence[Dict[str, Any]],
    review_by_ticker: Dict[str, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    confidence_by_ticker = {normalize_text(row.get("ticker")): row for row in confidence_rows if isinstance(row, dict)}
    rows: List[Dict[str, Any]] = []
    for pool_name, items in [("focus_pool", real_focus_rows), ("signal_pool", signal_rows)]:
        for item in items:
            valuation_source = normalize_text(item.get("valuation_source") or item.get("valuation_source_at_signal"))
            support = valuation_support_tier(valuation_source)
            if support in {"formal_core", "formal_support"}:
                continue
            ticker = normalize_text(item.get("ticker"))
            confidence = confidence_by_ticker.get(ticker, {})
            review = (review_by_ticker or {}).get(ticker.upper(), {})
            rows.append(
                {
                    "pool": pool_name,
                    "ticker": ticker,
                    "name": normalize_text(item.get("name")),
                    "method_group": normalize_text(item.get("method_group")),
                    "valuation_source": valuation_source,
                    "valuation_support_tier": support,
                    "trust_bucket": normalize_text(confidence.get("trust_bucket")),
                    "trust_grade": normalize_text(confidence.get("trust_grade")),
                    "suggested_action": normalize_text(confidence.get("suggested_action")),
                    "manual_review_decision": normalize_text(review.get("manual_review_decision")),
                    "manual_action": normalize_text(review.get("manual_action")),
                }
            )
    rows.sort(
        key=lambda row: (
            0 if normalize_text(row.get("pool")) == "signal_pool" else 1,
            quality_priority(normalize_text(row.get("valuation_support_tier"))),
            normalize_text(row.get("ticker")),
        )
    )
    return rows[:30]


def latest_as_of_date(meta_payload: Dict[str, Any], signals: Sequence[Dict[str, Any]]) -> str:
    candidates: List[str] = []
    dates = meta_payload.get("as_of_dates") or []
    if dates:
        candidates.append(normalize_text(dates[-1]))
    signal_dates = sorted({normalize_text(row.get("as_of_date")) for row in signals if normalize_text(row.get("as_of_date"))})
    if signal_dates:
        candidates.append(signal_dates[-1])
    candidates = [item for item in candidates if item]
    return max(candidates) if candidates else ""


def history_snapshot_record(
    *,
    as_of_date: str,
    universe_summary: Dict[str, Any],
    focus_summary: Dict[str, Any],
    signal_summary: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_date": as_of_date,
        "overall_real": {
            "formal_valuation_coverage_rate": universe_summary.get("formal_valuation_coverage_rate"),
            "price_fallback_rate": universe_summary.get("price_fallback_rate"),
        },
        "focus_pool": {
            "formal_valuation_coverage_rate": focus_summary.get("formal_valuation_coverage_rate"),
            "price_fallback_rate": focus_summary.get("price_fallback_rate"),
        },
        "signal_pool": {
            "formal_valuation_coverage_rate": signal_summary.get("formal_valuation_coverage_rate"),
            "price_fallback_rate": signal_summary.get("price_fallback_rate"),
        },
    }


def append_history(history_file: Path, record: Dict[str, Any]) -> None:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    existing = load_jsonl(history_file)
    if existing:
        last = existing[-1]
        comparable_last = {k: last.get(k) for k in ["as_of_date", "overall_real", "focus_pool", "signal_pool"]}
        comparable_new = {k: record.get(k) for k in ["as_of_date", "overall_real", "focus_pool", "signal_pool"]}
        if comparable_last == comparable_new:
            return
    with history_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def unique_trend_rows(history_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_date: Dict[str, Dict[str, Any]] = {}
    for row in history_rows:
        as_of = normalize_text(row.get("as_of_date"))
        if as_of:
            by_date[as_of] = row
    return [by_date[key] for key in sorted(by_date.keys())]


def build_valuation_coverage(
    *,
    real_rows: Sequence[Dict[str, Any]],
    signals: Sequence[Dict[str, Any]],
    positions: Sequence[Dict[str, Any]],
    focus_lookup: set[str],
    meta_payload: Dict[str, Any],
    confidence_payload: Dict[str, Any] | None = None,
    review_writeback_payload: Dict[str, Any] | None = None,
    history_rows: Sequence[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    history_rows = list(history_rows or [])
    real_focus_rows = [row for row in real_rows if row_lookup_keys(row) & focus_lookup]
    signal_rows = latest_signal_rows([dict(row) for row in signals])
    signal_summary = pool_summary(signal_rows, "valuation_source_at_signal")
    universe_summary = pool_summary(real_rows, "valuation_source")
    focus_summary = pool_summary(real_focus_rows, "valuation_source")

    positions_by_support: Dict[str, List[Dict[str, Any]]] = {}
    for row in positions:
        support = normalize_text(row.get("valuation_support_tier")) or valuation_support_tier(row.get("valuation_source_at_signal"))
        positions_by_support.setdefault(support, []).append(row)
    validation_by_support = {
        support: summarize_validation_rows(rows)
        for support, rows in sorted(positions_by_support.items())
    }

    confidence_rows = []
    if isinstance(confidence_payload, dict):
        confidence_rows = [row for row in (confidence_payload.get("opportunities") or []) if isinstance(row, dict)]
    active_signal_ids = {normalize_text(row.get("signal_id")) for row in signal_rows if normalize_text(row.get("signal_id"))}
    active_confidence_rows = [row for row in confidence_rows if normalize_text(row.get("signal_id")) in active_signal_ids]
    confidence_by_support: Dict[str, Dict[str, int]] = {}
    for support in sorted({valuation_support_tier(row.get("valuation_source_at_signal")) for row in signal_rows}):
        related = [row for row in active_confidence_rows if valuation_support_tier(row.get("valuation_source_at_signal")) == support]
        confidence_by_support[support] = summarize_confidence_rows(related)

    review_rows = reviewed_items(review_writeback_payload)
    review_by_ticker = reviewed_items_by_ticker(review_writeback_payload)
    manual_review = summarize_review_writeback(review_rows)
    sync_receipt = review_writeback_payload.get("sync_receipt") if isinstance(review_writeback_payload, dict) and isinstance(review_writeback_payload.get("sync_receipt"), dict) else {}
    load_receipt = review_writeback_payload.get("load_receipt") if isinstance(review_writeback_payload, dict) and isinstance(review_writeback_payload.get("load_receipt"), dict) else {}
    if sync_receipt:
        manual_review["sync_status"] = "ok" if sync_receipt.get("synced") else "degraded"
        manual_review["sync_reason"] = normalize_text(sync_receipt.get("reason"))
        manual_review["fallback_mode"] = normalize_text(sync_receipt.get("fallback_mode"))
    elif load_receipt:
        manual_review["sync_status"] = "degraded"
        manual_review["sync_reason"] = normalize_text(load_receipt.get("reason"))
        manual_review["fallback_mode"] = normalize_text(load_receipt.get("fallback_mode"))
    active_signal_tickers = {normalize_text(row.get("ticker")).upper() for row in signal_rows if normalize_text(row.get("ticker"))}
    manual_review["active_signal_reviewed_count"] = sum(
        1 for item in review_rows if normalize_text(item.get("ticker")).upper() in active_signal_tickers
    )
    gap_rows = build_gap_rows(
        real_focus_rows=real_focus_rows,
        signal_rows=signal_rows,
        confidence_rows=active_confidence_rows,
        review_by_ticker=review_by_ticker,
    )
    as_of_date = latest_as_of_date(meta_payload, signals)
    trend = unique_trend_rows(history_rows)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_date": as_of_date,
        "signal_pool_scope": "latest_signal_per_ticker",
        "validation_scope": "all_positions_history",
        "overall_real_universe": universe_summary,
        "focus_pool": focus_summary,
        "signal_pool": signal_summary,
        "validation_by_valuation_support": validation_by_support,
        "confidence_by_valuation_support": confidence_by_support,
        "manual_review": manual_review,
        "gap_rows": gap_rows,
        "trend": trend,
    }


def render_valuation_coverage_markdown(doc: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# 估值覆盖最新报表")
    lines.append("")
    lines.append(f"- 生成时间：{normalize_text(doc.get('generated_at_utc'))}")
    lines.append(f"- 截止日期：{normalize_text(doc.get('as_of_date')) or '-'}")
    lines.append(f"- signal 池口径：{normalize_text(doc.get('signal_pool_scope')) or 'latest_signal_per_ticker'}")
    lines.append(f"- 验证效果口径：{normalize_text(doc.get('validation_scope')) or 'all_positions_history'}")
    lines.append("")
    lines.append("## 池子覆盖")
    lines.append("")
    lines.append("| 池子 | 样本 | formal_core | formal_support | reference_only | price_fallback | formal覆盖率 | formal+reference覆盖率 | fallback占比 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for label, key in [("overall_real", "overall_real_universe"), ("focus_pool", "focus_pool"), ("signal_pool", "signal_pool")]:
        row = doc.get(key) or {}
        supports = row.get("valuation_support_breakdown") or {}
        lines.append(
            "| {label} | {count} | {formal_core} | {formal_support} | {reference_only} | {price_fallback} | {formal_rate} | {formal_reference_rate} | {fallback_rate} |".format(
                label=label,
                count=row.get("count", 0),
                formal_core=supports.get("formal_core", 0),
                formal_support=supports.get("formal_support", 0),
                reference_only=supports.get("reference_only", 0),
                price_fallback=supports.get("price_fallback", 0),
                formal_rate=_fmt_pct(row.get("formal_valuation_coverage_rate")),
                formal_reference_rate=_fmt_pct(row.get("formal_or_reference_coverage_rate")),
                fallback_rate=_fmt_pct(row.get("price_fallback_rate")),
            )
        )
    lines.append("")
    lines.append("## 信号池分层效果")
    lines.append("")
    lines.append("| 支持层级 | 样本 | 已评估 | Open | Closed | Expired | Pending | 平均净收益 | 一级超额 | 命中率 | 可信度分层 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for support, row in sorted((doc.get("validation_by_valuation_support") or {}).items()):
        confidence = (doc.get("confidence_by_valuation_support") or {}).get(support) or {}
        lines.append(
            "| {support} | {count} | {evaluated} | {open_count} | {closed_count} | {expired_count} | {pending_count} | {avg_return} | {avg_excess} | {hit_rate} | {confidence} |".format(
                support=support,
                count=row.get("count", 0),
                evaluated=row.get("evaluated_count", 0),
                open_count=row.get("open_count", 0),
                closed_count=row.get("closed_count", 0),
                expired_count=row.get("expired_count", 0),
                pending_count=row.get("pending_entry_count", 0),
                avg_return=_fmt_pct(row.get("avg_strategy_return_net")),
                avg_excess=_fmt_pct(row.get("avg_primary_excess_return")),
                hit_rate=_fmt_pct(row.get("hit_rate")),
                confidence=json.dumps(confidence, ensure_ascii=False),
            )
        )
    lines.append("")
    lines.append("## 人工复核闭环")
    lines.append("")
    manual_review = doc.get("manual_review") or {}
    lines.append(f"- 已人工复核：{int(manual_review.get('reviewed_items_count') or 0)}")
    lines.append(f"- 命中当前 signal 池：{int(manual_review.get('active_signal_reviewed_count') or 0)}")
    lines.append(f"- 待继续跟进：{int(manual_review.get('followup_backlog_count') or 0)}")
    if normalize_text(manual_review.get('sync_status')):
        lines.append(f"- 拉取状态：{normalize_text(manual_review.get('sync_status'))}")
    if normalize_text(manual_review.get('sync_reason')):
        lines.append(f"- 拉取说明：{normalize_text(manual_review.get('sync_reason'))}")
    if normalize_text(manual_review.get('fallback_mode')):
        lines.append(f"- 容错模式：{normalize_text(manual_review.get('fallback_mode'))}")
    lines.append("")
    lines.append("| 结论 | 数量 |")
    lines.append("|---|---:|")
    for key, value in sorted((manual_review.get('decision_breakdown') or {}).items()):
        lines.append(f"| {normalize_text(key)} | {int(value)} |")
    if not (manual_review.get('decision_breakdown') or {}):
        lines.append("| - | 0 |")
    lines.append("")
    lines.append("## 当前 gap")
    lines.append("")
    lines.append("| 池子 | 标的 | 方法组 | 估值来源 | 支持层级 | 可信度分层 | 建议动作 | 人工判定 | 人工动作 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in doc.get("gap_rows") or []:
        lines.append(
            "| {pool} | {name}({ticker}) | {method_group} | {valuation_source} | {support} | {trust_bucket} | {action} | {manual_decision} | {manual_action} |".format(
                pool=normalize_text(row.get("pool")),
                name=normalize_text(row.get("name")),
                ticker=normalize_text(row.get("ticker")),
                method_group=normalize_text(row.get("method_group")) or "-",
                valuation_source=normalize_text(row.get("valuation_source")) or "-",
                support=normalize_text(row.get("valuation_support_tier")) or "-",
                trust_bucket=normalize_text(row.get("trust_bucket")) or "-",
                action=normalize_text(row.get("suggested_action")) or "-",
                manual_decision=normalize_text(row.get("manual_review_decision")) or "-",
                manual_action=normalize_text(row.get("manual_action")) or "-",
            )
        )
    lines.append("")
    lines.append("## 趋势")
    lines.append("")
    lines.append("| 截止日 | overall formal覆盖率 | focus formal覆盖率 | signal formal覆盖率 | overall fallback占比 | signal fallback占比 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in doc.get("trend") or []:
        lines.append(
            "| {as_of} | {overall_formal} | {focus_formal} | {signal_formal} | {overall_fallback} | {signal_fallback} |".format(
                as_of=normalize_text(row.get("as_of_date")),
                overall_formal=_fmt_pct(((row.get("overall_real") or {}).get("formal_valuation_coverage_rate"))),
                focus_formal=_fmt_pct(((row.get("focus_pool") or {}).get("formal_valuation_coverage_rate"))),
                signal_formal=_fmt_pct(((row.get("signal_pool") or {}).get("formal_valuation_coverage_rate"))),
                overall_fallback=_fmt_pct(((row.get("overall_real") or {}).get("price_fallback_rate"))),
                signal_fallback=_fmt_pct(((row.get("signal_pool") or {}).get("price_fallback_rate"))),
            )
        )
    return "\n".join(lines) + "\n"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.2f}%"
