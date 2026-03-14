from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_PRIMARY_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "A": {
        "benchmark_id": "A_WIDE_CSI300",
        "benchmark_name": "沪深300",
        "provider_symbol_candidates": ["CSI300", "沪深300"],
    },
    "HK": {
        "benchmark_id": "HK_WIDE_HSI",
        "benchmark_name": "恒生指数",
        "provider_symbol_candidates": ["HSI", "恒生指数"],
    },
    "US": {
        "benchmark_id": "US_WIDE_SPX",
        "benchmark_name": "标普500",
        "provider_symbol_candidates": ["SPX", "S&P500", "标普500"],
    },
}

DEFAULT_SECONDARY_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "A_CONSUMPTION_CORE": {
        "benchmark_id": "A_CONSUMPTION_CORE",
        "benchmark_name": "A股质量消费核心基准",
        "market_scope": "A",
    },
    "A_TECH_GROWTH": {
        "benchmark_id": "A_TECH_GROWTH",
        "benchmark_name": "A股科技成长基准",
        "market_scope": "A",
    },
    "A_SEMI_AI": {
        "benchmark_id": "A_SEMI_AI",
        "benchmark_name": "A股半导体/AI 基准",
        "market_scope": "A",
    },
    "A_NEW_ENERGY_MANUFACTURING": {
        "benchmark_id": "A_NEW_ENERGY_MANUFACTURING",
        "benchmark_name": "A股新能源/高端制造基准",
        "market_scope": "A",
    },
    "A_HEALTHCARE_BIOTECH": {
        "benchmark_id": "A_HEALTHCARE_BIOTECH",
        "benchmark_name": "A股医药/生物科技基准",
        "market_scope": "A",
    },
    "A_RESOURCE_CYCLICAL": {
        "benchmark_id": "A_RESOURCE_CYCLICAL",
        "benchmark_name": "A股资源/周期基准",
        "market_scope": "A",
    },
    "A_FIN_PROPERTY": {
        "benchmark_id": "A_FIN_PROPERTY",
        "benchmark_name": "A股金融地产基准",
        "market_scope": "A",
    },
    "HK_TECH_PLATFORM": {
        "benchmark_id": "HK_TECH_PLATFORM",
        "benchmark_name": "港股科技平台基准",
        "market_scope": "HK",
    },
    "HK_CONSUMER_PLATFORM": {
        "benchmark_id": "HK_CONSUMER_PLATFORM",
        "benchmark_name": "港股消费/平台基准",
        "market_scope": "HK",
    },
    "HK_FIN_PROPERTY": {
        "benchmark_id": "HK_FIN_PROPERTY",
        "benchmark_name": "港股金融地产基准",
        "market_scope": "HK",
    },
    "HK_HEALTHCARE_BIOTECH": {
        "benchmark_id": "HK_HEALTHCARE_BIOTECH",
        "benchmark_name": "港股医药生科基准",
        "market_scope": "HK",
    },
    "US_TECH_GROWTH": {
        "benchmark_id": "US_TECH_GROWTH",
        "benchmark_name": "美股科技成长基准",
        "market_scope": "US",
    },
    "US_SEMI_AI": {
        "benchmark_id": "US_SEMI_AI",
        "benchmark_name": "美股半导体/AI 基准",
        "market_scope": "US",
    },
    "US_CONSUMER_PLATFORM": {
        "benchmark_id": "US_CONSUMER_PLATFORM",
        "benchmark_name": "美股消费/平台基准",
        "market_scope": "US",
    },
    "US_CLOUD_SOFTWARE": {
        "benchmark_id": "US_CLOUD_SOFTWARE",
        "benchmark_name": "美股云软件基准",
        "market_scope": "US",
    },
    "US_HEALTHCARE_BIOTECH": {
        "benchmark_id": "US_HEALTHCARE_BIOTECH",
        "benchmark_name": "美股医药生物科技基准",
        "market_scope": "US",
    },
    "US_ENERGY_INDUSTRIAL_DEFENSE": {
        "benchmark_id": "US_ENERGY_INDUSTRIAL_DEFENSE",
        "benchmark_name": "美股能源/工业/防务基准",
        "market_scope": "US",
    },
}

MARKET_SECTOR_SECONDARY_MAP: Dict[str, Dict[str, str]] = {
    "A": {
        "TECHNOLOGY": "A_TECH_GROWTH",
        "SEMICONDUCTORS": "A_SEMI_AI",
        "HEALTHCARE": "A_HEALTHCARE_BIOTECH",
        "CONSUMER STAPLES": "A_CONSUMPTION_CORE",
        "CONSUMER DISCRETIONARY": "A_CONSUMPTION_CORE",
        "ENERGY": "A_RESOURCE_CYCLICAL",
        "MATERIALS": "A_RESOURCE_CYCLICAL",
        "INDUSTRIALS": "A_NEW_ENERGY_MANUFACTURING",
        "FINANCIAL SERVICES": "A_FIN_PROPERTY",
        "REAL ESTATE": "A_FIN_PROPERTY",
    },
    "HK": {
        "TECHNOLOGY": "HK_TECH_PLATFORM",
        "COMMUNICATION SERVICES": "HK_TECH_PLATFORM",
        "CONSUMER DISCRETIONARY": "HK_CONSUMER_PLATFORM",
        "CONSUMER STAPLES": "HK_CONSUMER_PLATFORM",
        "FINANCIAL SERVICES": "HK_FIN_PROPERTY",
        "REAL ESTATE": "HK_FIN_PROPERTY",
        "HEALTHCARE": "HK_HEALTHCARE_BIOTECH",
    },
    "US": {
        "TECHNOLOGY": "US_TECH_GROWTH",
        "COMMUNICATION SERVICES": "US_TECH_GROWTH",
        "CONSUMER DISCRETIONARY": "US_CONSUMER_PLATFORM",
        "CONSUMER STAPLES": "US_CONSUMER_PLATFORM",
        "HEALTHCARE": "US_HEALTHCARE_BIOTECH",
        "ENERGY": "US_ENERGY_INDUSTRIAL_DEFENSE",
        "INDUSTRIALS": "US_ENERGY_INDUSTRIAL_DEFENSE",
    },
}

GROUP_EXIT_TEMPLATE_MAP: Dict[str, str] = {
    "value_quality_compound": "value_quality_compound",
    "industry_compounder": "industry_compounder",
    "garp_growth": "garp_growth",
    "deep_value_recovery": "deep_value_recovery",
    "macro_regime": "macro_regime",
    "trend_following": "trend_following",
    "systematic_quant": "systematic_quant",
    "event_driven_activist": "event_driven_activist",
    "credit_cycle": "credit_cycle",
}

NOTE_PAIR_RE = re.compile(r"\b(close|target|upside|fv_source|dcf_symbol|dcf_iv)=([^|]+)")
AS_OF_DATE_RE = re.compile(r"real-data@(\d{4}-\d{2}-\d{2})")


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]



def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))



def as_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None



def normalize_text(value: Any) -> str:
    return str(value or "").strip()



def normalize_ticker(raw: Any) -> str:
    return normalize_text(raw).upper()


def markdown_cell(value: Any) -> str:
    text = normalize_text(value)
    return text.replace("|", "/")



def normalize_internal_symbol_for_ticker(ticker: Any) -> str:
    raw = normalize_ticker(ticker)
    if not raw:
        return ""
    if raw.startswith(("SH.", "SZ.", "HK.", "US.")):
        return raw
    if raw.endswith(".SS") and raw[:-3].isdigit():
        return f"SH.{raw[:-3]}"
    if raw.endswith(".SZ") and raw[:-3].isdigit():
        return f"SZ.{raw[:-3]}"
    if raw.endswith(".HK"):
        code = raw[:-3]
        if code.isdigit():
            return f"HK.{int(code):05d}"
    return f"US.{raw.replace('.', '-')}"



def ticker_lookup_keys(raw: Any) -> List[str]:
    ticker = normalize_ticker(raw)
    if not ticker:
        return []
    keys: List[str] = []

    def add(value: str) -> None:
        normalized = normalize_ticker(value)
        if normalized and normalized not in keys:
            keys.append(normalized)

    add(ticker)
    if ticker.startswith(("SH.", "SZ.", "HK.", "US.")):
        add(dcf_symbol_to_ticker(ticker))
    elif ticker.endswith(".HK"):
        code = ticker[:-3]
        if code.isdigit():
            add(f"{int(code)}.HK")
            add(f"{int(code):05d}.HK")
            add(f"HK.{int(code):05d}")
    elif ticker.endswith(".SS") and ticker[:-3].isdigit():
        add(f"SH.{ticker[:-3]}")
    elif ticker.endswith(".SZ") and ticker[:-3].isdigit():
        add(f"SZ.{ticker[:-3]}")
    else:
        add(f"US.{ticker}")
    return keys



def dcf_symbol_to_ticker(dcf_symbol: Any) -> str:
    raw = normalize_ticker(dcf_symbol)
    if not raw or "." not in raw:
        return raw
    market, code = raw.split(".", 1)
    if market == "US":
        return code
    if market == "HK":
        try:
            return f"{int(code):04d}.HK"
        except ValueError:
            return f"{code}.HK"
    if market == "SH":
        return f"{code}.SS"
    if market == "SZ":
        return f"{code}.SZ"
    return raw



def parse_note_fields(note: Any) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    text = normalize_text(note)
    for key, value in NOTE_PAIR_RE.findall(text):
        fields[key] = normalize_text(value)
    return fields



def extract_as_of_date(note: Any, fallback: str = "") -> str:
    text = normalize_text(note)
    match = AS_OF_DATE_RE.search(text)
    if match:
        return match.group(1)
    return fallback



def load_focus_tickers(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    payload = read_json(path)
    if isinstance(payload, dict):
        raw_items = payload.get("symbols", [])
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raw_items = []

    tickers: set[str] = set()
    for raw in raw_items:
        if isinstance(raw, str):
            ticker = dcf_symbol_to_ticker(raw)
        elif isinstance(raw, dict):
            ticker = normalize_text(raw.get("ticker") or dcf_symbol_to_ticker(raw.get("dcf_symbol") or raw.get("symbol")))
        else:
            ticker = ""
        for key in ticker_lookup_keys(ticker):
            tickers.add(key)
    return tickers



def build_row_index(rows: Iterable[Dict[str, Any]], *keys: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        for field in keys:
            value = row.get(field)
            for key in ticker_lookup_keys(value):
                index.setdefault(key, row)
    return index



def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()



def make_signal_id(source_list_id: str, as_of_date: str, ticker: str) -> str:
    payload = f"{normalize_text(source_list_id)}|{normalize_text(as_of_date)}|{normalize_ticker(ticker)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]



def load_benchmark_config(path: Path | None) -> Dict[str, Any]:
    if path and path.exists():
        payload = read_json(path)
        primary = payload.get("primary_benchmarks") if isinstance(payload, dict) else None
        secondary = payload.get("secondary_benchmarks") if isinstance(payload, dict) else None
        secondary_index = {
            str(item.get("benchmark_id") or "").strip(): item
            for item in (secondary or [])
            if isinstance(item, dict) and item.get("benchmark_id")
        }
        return {
            "primary_benchmarks": primary or DEFAULT_PRIMARY_BENCHMARKS,
            "secondary_benchmarks": secondary_index or DEFAULT_SECONDARY_BENCHMARKS,
        }
    return {
        "primary_benchmarks": DEFAULT_PRIMARY_BENCHMARKS,
        "secondary_benchmarks": DEFAULT_SECONDARY_BENCHMARKS,
    }



def primary_benchmark_for_market(market: str, benchmark_config: Dict[str, Any]) -> Dict[str, Any]:
    primary = benchmark_config.get("primary_benchmarks") or DEFAULT_PRIMARY_BENCHMARKS
    market_key = normalize_text(market).upper() or "US"
    info = primary.get(market_key) or DEFAULT_PRIMARY_BENCHMARKS.get(market_key) or DEFAULT_PRIMARY_BENCHMARKS["US"]
    return {
        "benchmark_id": info.get("benchmark_id"),
        "benchmark_name": info.get("benchmark_name"),
        "provider_symbol_candidates": info.get("provider_symbol_candidates") or [],
        "reason": "market_primary_default",
    }



def secondary_benchmark_for_signal(
    *,
    market: str,
    sector: str,
    primary_benchmark: Dict[str, Any],
    benchmark_config: Dict[str, Any],
) -> Dict[str, Any]:
    market_key = normalize_text(market).upper()
    sector_key = normalize_text(sector).upper()
    secondary_lookup = benchmark_config.get("secondary_benchmarks") or DEFAULT_SECONDARY_BENCHMARKS
    benchmark_id = MARKET_SECTOR_SECONDARY_MAP.get(market_key, {}).get(sector_key)
    if benchmark_id and benchmark_id in secondary_lookup:
        info = secondary_lookup[benchmark_id]
        return {
            "benchmark_id": info.get("benchmark_id"),
            "benchmark_name": info.get("benchmark_name"),
            "reason": f"sector_match:{sector_key.lower()}",
            "confidence": "high",
        }
    return {
        "benchmark_id": primary_benchmark.get("benchmark_id"),
        "benchmark_name": primary_benchmark.get("benchmark_name"),
        "reason": "fallback_to_primary",
        "confidence": "fallback_to_primary",
    }



def determine_review_state(real_row: Dict[str, Any] | None) -> Tuple[str, str]:
    if real_row is None:
        return "blocked", "missing_real_row"
    valuation_source = normalize_text(real_row.get("valuation_source"))
    dcf_quality_gate_status = normalize_text(real_row.get("dcf_quality_gate_status")).lower()
    if dcf_quality_gate_status in {"fail", "blocked"}:
        return "blocked", f"dcf_quality_gate:{dcf_quality_gate_status}"
    if valuation_source == "close_fallback":
        return "escalated", "valuation_source=close_fallback"
    if dcf_quality_gate_status in {"caution", "warn"}:
        return "escalated", f"dcf_quality_gate:{dcf_quality_gate_status}"
    return "auto", "passed_default_gate"


def valuation_support_tier_local(valuation_source: Any) -> str:
    source = normalize_text(valuation_source)
    if source == "dcf_iv_base":
        return "formal_core"
    if source == "dcf_external_consensus":
        return "formal_support"
    if source == "target_mean_price":
        return "reference_only"
    if source == "close_fallback":
        return "price_fallback"
    return "unknown"


def valuation_support_rank(valuation_source: Any) -> int:
    return {
        "price_fallback": 0,
        "reference_only": 1,
        "unknown": 2,
        "formal_support": 3,
        "formal_core": 4,
    }.get(valuation_support_tier_local(valuation_source), -1)


def latest_entries_by_ticker(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ticker = normalize_text(row.get("ticker"))
        if not ticker:
            continue
        current = latest.get(ticker)
        sort_key = (
            normalize_text(row.get("as_of_date")),
            normalize_text(row.get("signal_generated_at_utc")),
            normalize_text(row.get("source_list_id")),
        )
        current_key = (
            normalize_text(current.get("as_of_date")) if current else "",
            normalize_text(current.get("signal_generated_at_utc")) if current else "",
            normalize_text(current.get("source_list_id")) if current else "",
        )
        if current is None or sort_key >= current_key:
            latest[ticker] = row
    return latest


def _current_price_from_real_row(real_row: Dict[str, Any] | None) -> float | None:
    if not isinstance(real_row, dict):
        return None
    note_fields = parse_note_fields(real_row.get("note"))
    for value in [
        note_fields.get("close"),
        real_row.get("close"),
        real_row.get("price"),
    ]:
        parsed = as_float(value)
        if parsed is not None and parsed > 0:
            return parsed
    return None


def _margin_of_safety_from_price_and_fair_value(price: float | None, fair_value: float | None) -> float | None:
    if price is None or fair_value is None or price <= 0 or fair_value <= 0:
        return None
    return 1.0 - (price / fair_value)



def resolve_exit_template_id(best_group_id: Any) -> str:
    group_id = normalize_text(best_group_id)
    return GROUP_EXIT_TEMPLATE_MAP.get(group_id, group_id or "unassigned")



def resolve_group_trace(top_row: Dict[str, Any], trace_row: Dict[str, Any] | None) -> Dict[str, Any] | None:
    best_group_id = normalize_text(top_row.get("explain_best_group_id"))
    encoded = normalize_text(top_row.get("explain_group_trace_json"))
    groups: List[Dict[str, Any]] = []
    if encoded:
        try:
            payload = json.loads(encoded)
            if isinstance(payload, list):
                groups = [item for item in payload if isinstance(item, dict)]
        except json.JSONDecodeError:
            groups = []
    if not groups and isinstance(trace_row, dict):
        raw_groups = trace_row.get("groups") or []
        if isinstance(raw_groups, list):
            groups = [item for item in raw_groups if isinstance(item, dict)]
    if best_group_id:
        for group in groups:
            if normalize_text(group.get("group_id")) == best_group_id:
                return group
    return groups[0] if groups else None



def build_artifact_refs(paths: Dict[str, Path], top_row: Dict[str, Any], real_row: Dict[str, Any] | None, trace_row: Dict[str, Any] | None, meta_payload: Dict[str, Any]) -> Dict[str, Any]:
    artifacts = []
    for kind, path in paths.items():
        item = {
            "kind": kind,
            "path": str(path),
            "exists": path.exists(),
        }
        if path.exists():
            item["sha256"] = sha256_file(path)
        artifacts.append(item)

    return {
        "artifacts": artifacts,
        "top_row_ref": {
            "ticker": normalize_text(top_row.get("ticker")),
            "best_group": normalize_text(top_row.get("best_group")),
            "best_group_id": normalize_text(top_row.get("explain_best_group_id")),
            "composite_score": as_float(top_row.get("composite_score")),
        },
        "real_row_ref": {
            "ticker": normalize_text(real_row.get("ticker")) if real_row else "",
            "valuation_source": normalize_text(real_row.get("valuation_source")) if real_row else "",
            "dcf_symbol": normalize_text(real_row.get("dcf_symbol")) if real_row else "",
        },
        "trace_ref": {
            "ticker": normalize_text(trace_row.get("ticker")) if trace_row else "",
            "group_count": len(trace_row.get("groups") or []) if trace_row else 0,
        },
        "meta_ref": {
            "generated_at_utc": normalize_text(meta_payload.get("generated_at_utc")),
            "as_of_dates": meta_payload.get("as_of_dates") or [],
        },
    }



def build_signal_entry(
    *,
    top_row: Dict[str, Any],
    real_row: Dict[str, Any] | None,
    trace_row: Dict[str, Any] | None,
    meta_payload: Dict[str, Any],
    benchmark_config: Dict[str, Any],
    source_list_id: str,
    source_rank: int,
    strategy_version: str,
    artifact_paths: Dict[str, Path],
) -> Dict[str, Any]:
    ticker = normalize_text(top_row.get("ticker"))
    market = normalize_text(top_row.get("market")) or normalize_text(top_row.get("explain_market")) or (
        normalize_text(trace_row.get("market")) if trace_row else ""
    )
    symbol = normalize_text(real_row.get("dcf_symbol")) if real_row else ""
    if not symbol:
        symbol = normalize_internal_symbol_for_ticker(ticker)

    note = normalize_text((real_row or {}).get("note") or top_row.get("note"))
    note_fields = parse_note_fields(note)
    as_of_date = extract_as_of_date(note, fallback=(meta_payload.get("as_of_dates") or [""])[-1] if meta_payload.get("as_of_dates") else "")
    price_at_signal = as_float(note_fields.get("close"))
    fair_value_at_signal = as_float((real_row or {}).get("fair_value"))
    if fair_value_at_signal is None:
        fair_value_at_signal = as_float(note_fields.get("target"))
    review_state, review_reason = determine_review_state(real_row)
    primary_benchmark = primary_benchmark_for_market(market, benchmark_config)
    secondary_benchmark = secondary_benchmark_for_signal(
        market=market,
        sector=normalize_text(top_row.get("sector") or (real_row or {}).get("sector")),
        primary_benchmark=primary_benchmark,
        benchmark_config=benchmark_config,
    )
    group_trace = resolve_group_trace(top_row, trace_row)
    signal_id = make_signal_id(source_list_id, as_of_date, ticker)

    return {
        "signal_id": signal_id,
        "signal_generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_list_id": source_list_id,
        "source_rank": source_rank,
        "as_of_date": as_of_date,
        "ticker": ticker,
        "symbol": symbol,
        "market": market,
        "name": normalize_text(top_row.get("name") or (real_row or {}).get("name")),
        "sector": normalize_text(top_row.get("sector") or (real_row or {}).get("sector")),
        "method_group": normalize_text(top_row.get("best_group")),
        "method_group_id": normalize_text(top_row.get("explain_best_group_id")) or normalize_text(top_row.get("best_group")),
        "method_family": normalize_text(top_row.get("best_group")),
        "method_family_id": normalize_text(top_row.get("explain_best_group_id")) or normalize_text(top_row.get("best_group")),
        "strategy_version": strategy_version,
        "signal_origin": "top_ranked_candidate",
        "entry_reason_summary": normalize_text(top_row.get("best_reason")),
        "price_at_signal": price_at_signal,
        "fair_value_at_signal": fair_value_at_signal,
        "margin_of_safety_at_signal": as_float(top_row.get("margin_of_safety")),
        "risk_control_at_signal": as_float(top_row.get("risk_control")),
        "composite_score_at_signal": as_float(top_row.get("composite_score")),
        "valuation_source_at_signal": normalize_text((real_row or {}).get("valuation_source") or note_fields.get("fv_source")),
        "valuation_source_detail_at_signal": normalize_text((real_row or {}).get("valuation_source_detail")),
        "primary_benchmark": primary_benchmark,
        "secondary_benchmark": secondary_benchmark,
        "exit_template_id": resolve_exit_template_id(top_row.get("explain_best_group_id") or top_row.get("best_group")),
        "review_state": review_state,
        "review_reason": review_reason,
        "trace_summary": {
            "tier": normalize_text((group_trace or {}).get("tier")),
            "tier_reason": normalize_text((group_trace or {}).get("tier_reason")),
            "hard_pass": bool((group_trace or {}).get("hard_pass", False)),
            "near_miss": bool((group_trace or {}).get("near_miss", False)),
            "weighted_contribution": as_float((group_trace or {}).get("weighted_contribution")),
            "base_score": as_float((group_trace or {}).get("base_score")),
            "adjusted_score": as_float((group_trace or {}).get("adjusted_score")),
            "hard_fail_reasons": (group_trace or {}).get("hard_fail_reasons") or [],
            "soft_penalties": [
                item.get("rule")
                for item in ((group_trace or {}).get("soft_penalties") or [])
                if isinstance(item, dict) and item.get("triggered")
            ],
        },
        "snapshot_refs": build_artifact_refs(
            paths=artifact_paths,
            top_row=top_row,
            real_row=real_row,
            trace_row=trace_row,
            meta_payload=meta_payload,
        ),
    }



def build_signal_entries(
    *,
    top_rows: List[Dict[str, Any]],
    real_rows: List[Dict[str, Any]],
    trace_payload: Dict[str, Any],
    meta_payload: Dict[str, Any],
    benchmark_config: Dict[str, Any],
    artifact_paths: Dict[str, Path],
    source_list_id: str,
    focus_tickers: set[str] | None = None,
) -> List[Dict[str, Any]]:
    focus_keys = focus_tickers or set()
    real_index = build_row_index(real_rows, "ticker", "dcf_symbol")
    trace_rows = trace_payload.get("rows") or []
    trace_index = build_row_index(trace_rows, "ticker")
    rulebook_version = normalize_text(trace_payload.get("rulebook_version")) or "v4"
    strategy_version = f"top20_pack_v4::{rulebook_version}"

    entries: List[Dict[str, Any]] = []
    for idx, top_row in enumerate(top_rows, start=1):
        ticker = normalize_text(top_row.get("ticker"))
        row_keys = set(ticker_lookup_keys(ticker))
        if row_keys & focus_keys:
            continue
        lookup_key = next(iter(row_keys), ticker)
        real_row = None
        for key in ticker_lookup_keys(ticker):
            real_row = real_index.get(key)
            if real_row is not None:
                break
        trace_row = None
        for key in ticker_lookup_keys(ticker):
            trace_row = trace_index.get(key)
            if trace_row is not None:
                break
        entries.append(
            build_signal_entry(
                top_row=top_row,
                real_row=real_row,
                trace_row=trace_row,
                meta_payload=meta_payload,
                benchmark_config=benchmark_config,
                source_list_id=source_list_id,
                source_rank=idx,
                strategy_version=strategy_version,
                artifact_paths=artifact_paths,
            )
        )
    return entries



def build_refresh_reissue_entries(
    *,
    ledger_entries: List[Dict[str, Any]],
    current_batch_entries: List[Dict[str, Any]],
    real_rows: List[Dict[str, Any]],
    meta_payload: Dict[str, Any],
    artifact_paths: Dict[str, Path],
    refresh_source_list_id: str,
    focus_tickers: set[str] | None = None,
) -> List[Dict[str, Any]]:
    focus_keys = focus_tickers or set()
    current_batch_tickers = {normalize_text(item.get("ticker")) for item in current_batch_entries if normalize_text(item.get("ticker"))}
    latest_history = latest_entries_by_ticker(ledger_entries)
    real_index = build_row_index(real_rows, "ticker", "dcf_symbol")
    meta_as_of_date = normalize_text((meta_payload.get("as_of_dates") or [""])[-1]) if (meta_payload.get("as_of_dates") or []) else ""

    entries: List[Dict[str, Any]] = []
    for ticker, previous_entry in sorted(latest_history.items()):
        row_keys = set(ticker_lookup_keys(ticker))
        if row_keys & focus_keys:
            continue
        if ticker in current_batch_tickers:
            continue
        real_row = None
        for key in ticker_lookup_keys(ticker):
            real_row = real_index.get(key)
            if real_row is not None:
                break
        if real_row is None:
            continue
        current_source = normalize_text(real_row.get("valuation_source"))
        previous_source = normalize_text(previous_entry.get("valuation_source_at_signal"))
        if valuation_support_rank(current_source) <= valuation_support_rank(previous_source):
            continue
        current_as_of_date = extract_as_of_date(real_row.get("note"), fallback=meta_as_of_date)
        symbol = normalize_text(real_row.get("dcf_symbol")) or normalize_text(previous_entry.get("symbol")) or normalize_internal_symbol_for_ticker(ticker)
        current_price = _current_price_from_real_row(real_row)
        current_fair_value = as_float(real_row.get("fair_value"))
        review_state, review_reason = determine_review_state(real_row)
        surrogate_top_row = {
            "ticker": ticker,
            "best_group": previous_entry.get("method_group"),
            "explain_best_group_id": previous_entry.get("method_group_id"),
            "composite_score": previous_entry.get("composite_score_at_signal"),
        }
        entry = {
            "signal_id": make_signal_id(refresh_source_list_id, current_as_of_date, ticker),
            "signal_generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_list_id": refresh_source_list_id,
            "source_rank": previous_entry.get("source_rank"),
            "as_of_date": current_as_of_date,
            "ticker": ticker,
            "symbol": symbol,
            "market": normalize_text(previous_entry.get("market") or real_row.get("market")),
            "name": normalize_text(real_row.get("name") or previous_entry.get("name")),
            "sector": normalize_text(real_row.get("sector") or previous_entry.get("sector")),
            "method_group": normalize_text(previous_entry.get("method_group")),
            "method_group_id": normalize_text(previous_entry.get("method_group_id")),
            "method_family": normalize_text(previous_entry.get("method_family") or previous_entry.get("method_group")),
            "method_family_id": normalize_text(previous_entry.get("method_family_id") or previous_entry.get("method_group_id")),
            "strategy_version": f"{normalize_text(previous_entry.get('strategy_version')) or 'top20_pack_v4'}::refresh_reissue",
            "signal_origin": "refresh_reissue",
            "entry_reason_summary": f"signal_refresh_reissue:{previous_source}->{current_source}",
            "price_at_signal": current_price,
            "fair_value_at_signal": current_fair_value,
            "margin_of_safety_at_signal": _margin_of_safety_from_price_and_fair_value(current_price, current_fair_value),
            "risk_control_at_signal": as_float(previous_entry.get("risk_control_at_signal")),
            "composite_score_at_signal": as_float(previous_entry.get("composite_score_at_signal")),
            "valuation_source_at_signal": current_source,
            "valuation_source_detail_at_signal": normalize_text(real_row.get("valuation_source_detail")),
            "primary_benchmark": previous_entry.get("primary_benchmark") or {},
            "secondary_benchmark": previous_entry.get("secondary_benchmark") or {},
            "exit_template_id": normalize_text(previous_entry.get("exit_template_id")),
            "review_state": review_state,
            "review_reason": f"signal_refresh_reissue:{previous_source}->{current_source};{review_reason}",
            "refresh_reissue_of_signal_id": normalize_text(previous_entry.get("signal_id")),
            "refresh_reissue_trigger": "valuation_source_upgrade",
            "previous_signal_as_of_date": normalize_text(previous_entry.get("as_of_date")),
            "previous_valuation_source_at_signal": previous_source,
            "previous_review_state": normalize_text(previous_entry.get("review_state")),
            "trace_summary": previous_entry.get("trace_summary") or {},
            "snapshot_refs": build_artifact_refs(
                paths=artifact_paths,
                top_row=surrogate_top_row,
                real_row=real_row,
                trace_row=None,
                meta_payload=meta_payload,
            ),
        }
        entries.append(entry)
    return entries


def load_existing_signal_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            signal_id = normalize_text(payload.get("signal_id"))
            if signal_id:
                ids.add(signal_id)
    return ids



def append_signal_entries(path: Path, entries: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for entry in entries:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")



def load_ledger_entries(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows



def _breakdown(rows: Iterable[Dict[str, Any]], field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        key = normalize_text(row.get(field)) or "<empty>"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))



def build_latest_summary(
    *,
    ledger_path: Path,
    ledger_entries: List[Dict[str, Any]],
    batch_entries: List[Dict[str, Any]],
    newly_appended_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    latest_as_of_date = ""
    all_dates = sorted(
        {normalize_text(item.get("as_of_date")) for item in ledger_entries if normalize_text(item.get("as_of_date"))}
    )
    if all_dates:
        latest_as_of_date = all_dates[-1]
    latest_batch = list(batch_entries) if batch_entries else ([
        item for item in ledger_entries if normalize_text(item.get("as_of_date")) == latest_as_of_date
    ] if latest_as_of_date else [])
    latest_batch_sorted = sorted(
        latest_batch,
        key=lambda item: (
            normalize_text(item.get("as_of_date")),
            normalize_text(item.get("signal_generated_at_utc")),
            float(item.get("composite_score_at_signal") or 0.0),
        ),
        reverse=True,
    )
    refresh_entries = [item for item in latest_batch_sorted if normalize_text(item.get("signal_origin")) == "refresh_reissue"]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ledger_file": str(ledger_path),
        "total_signals": len(ledger_entries),
        "distinct_signal_dates": len({normalize_text(item.get("as_of_date")) for item in ledger_entries if normalize_text(item.get("as_of_date"))}),
        "latest_as_of_date": latest_as_of_date,
        "latest_batch_as_of_dates": sorted({normalize_text(item.get("as_of_date")) for item in latest_batch_sorted if normalize_text(item.get("as_of_date"))}),
        "latest_batch_scope": "current_run_candidates" if batch_entries else "latest_signal_date",
        "latest_signal_count": len(latest_batch_sorted),
        "newly_appended_count": len(newly_appended_entries),
        "latest_batch_method_group_breakdown": _breakdown(latest_batch_sorted, "method_group"),
        "latest_batch_valuation_source_breakdown": _breakdown(latest_batch_sorted, "valuation_source_at_signal"),
        "latest_batch_review_state_breakdown": _breakdown(latest_batch_sorted, "review_state"),
        "latest_batch_signal_origin_breakdown": _breakdown(latest_batch_sorted, "signal_origin"),
        "latest_batch_source_list_breakdown": _breakdown(latest_batch_sorted, "source_list_id"),
        "latest_batch_refresh_reissue_count": len(refresh_entries),
        "latest_refresh_reissue_signals": [
            {
                "ticker": item.get("ticker"),
                "name": item.get("name"),
                "previous_signal_as_of_date": item.get("previous_signal_as_of_date"),
                "previous_valuation_source_at_signal": item.get("previous_valuation_source_at_signal"),
                "valuation_source_at_signal": item.get("valuation_source_at_signal"),
                "review_state": item.get("review_state"),
                "entry_reason_summary": item.get("entry_reason_summary"),
            }
            for item in refresh_entries[:20]
        ],
        "latest_batch_signals": [
            {
                "source_rank": item.get("source_rank"),
                "ticker": item.get("ticker"),
                "name": item.get("name"),
                "method_group": item.get("method_group"),
                "signal_origin": item.get("signal_origin"),
                "source_list_id": item.get("source_list_id"),
                "composite_score_at_signal": item.get("composite_score_at_signal"),
                "price_at_signal": item.get("price_at_signal"),
                "fair_value_at_signal": item.get("fair_value_at_signal"),
                "valuation_source_at_signal": item.get("valuation_source_at_signal"),
                "review_state": item.get("review_state"),
                "entry_reason_summary": item.get("entry_reason_summary"),
            }
            for item in latest_batch_sorted[:20]
        ],
    }
    return summary


def render_latest_markdown(summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# 前瞻信号账本最新摘要")
    lines.append("")
    lines.append(f"- 生成时间：{normalize_text(summary.get('generated_at_utc'))}")
    lines.append(f"- 账本文件：`{normalize_text(summary.get('ledger_file'))}`")
    lines.append(f"- 账本累计信号数：{summary.get('total_signals', 0)}")
    lines.append(f"- 信号日期数：{summary.get('distinct_signal_dates', 0)}")
    lines.append(f"- 最新信号日期：{normalize_text(summary.get('latest_as_of_date')) or '-'}")
    lines.append(f"- 本轮候选日期：`{json.dumps(summary.get('latest_batch_as_of_dates') or [], ensure_ascii=False)}`")
    lines.append(f"- 本轮候选信号数：{summary.get('latest_signal_count', 0)}")
    lines.append(f"- 本次新增：{summary.get('newly_appended_count', 0)}")
    lines.append(f"- 本轮来源类型：`{json.dumps(summary.get('latest_batch_signal_origin_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 本轮 source_list：`{json.dumps(summary.get('latest_batch_source_list_breakdown') or {}, ensure_ascii=False)}`")
    lines.append("")

    lines.append("## 最新批次分布")
    lines.append("")
    lines.append(f"- 方法分组：`{json.dumps(summary.get('latest_batch_method_group_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 估值来源：`{json.dumps(summary.get('latest_batch_valuation_source_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 复核状态：`{json.dumps(summary.get('latest_batch_review_state_breakdown') or {}, ensure_ascii=False)}`")
    lines.append("")

    if summary.get("latest_batch_refresh_reissue_count"):
        lines.append("## 本轮重发")
        lines.append("")
        lines.append("| 标的 | 原信号日 | 原来源 | 当前来源 | 复核状态 | 触发原因 |")
        lines.append("|---|---|---|---|---|---|")
        for row in summary.get("latest_refresh_reissue_signals") or []:
            lines.append(
                "| {name}({ticker}) | {previous_date} | {previous_source} | {current_source} | {review_state} | {reason} |".format(
                    name=markdown_cell(row.get("name")) or "-",
                    ticker=markdown_cell(row.get("ticker")) or "-",
                    previous_date=markdown_cell(row.get("previous_signal_as_of_date")) or "-",
                    previous_source=markdown_cell(row.get("previous_valuation_source_at_signal")) or "-",
                    current_source=markdown_cell(row.get("valuation_source_at_signal")) or "-",
                    review_state=markdown_cell(row.get("review_state")) or "-",
                    reason=markdown_cell(row.get("entry_reason_summary")) or "-",
                )
            )
        lines.append("")

    lines.append("## 最新批次信号")
    lines.append("")
    lines.append("| 排名 | 标的 | 方法 | 来源类型 | 综合分 | 现价 | 公允价值 | 估值来源 | 复核状态 | 入选理由 |")
    lines.append("|---|---|---|---|---:|---:|---:|---|---|---|")
    for row in summary.get("latest_batch_signals") or []:
        lines.append(
            "| {rank} | {name}({ticker}) | {group} | {origin} | {score} | {price} | {fair_value} | {valuation_source} | {review_state} | {reason} |".format(
                rank=row.get("source_rank") or "-",
                name=markdown_cell(row.get("name")) or "-",
                ticker=markdown_cell(row.get("ticker")) or "-",
                group=markdown_cell(row.get("method_group")) or "-",
                origin=markdown_cell(row.get("signal_origin")) or "-",
                score=(f"{float(row.get('composite_score_at_signal')):.2f}" if row.get("composite_score_at_signal") is not None else "-"),
                price=(f"{float(row.get('price_at_signal')):.2f}" if row.get("price_at_signal") is not None else "-"),
                fair_value=(f"{float(row.get('fair_value_at_signal')):.2f}" if row.get("fair_value_at_signal") is not None else "-"),
                valuation_source=markdown_cell(row.get("valuation_source_at_signal")) or "-",
                review_state=markdown_cell(row.get("review_state")) or "-",
                reason=markdown_cell(row.get("entry_reason_summary")) or "-",
            )
        )
    return "\n".join(lines) + "\n"
