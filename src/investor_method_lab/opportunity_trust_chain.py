from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from investor_method_lab.signal_ledger import (
    load_ledger_entries,
    normalize_internal_symbol_for_ticker,
    normalize_text,
    read_json,
    ticker_lookup_keys,
)

HOME_DIR = Path.home()


def resolve_hit_zone_data_dir() -> Path:
    candidates = [
        os.getenv("HIT_ZONE_PROJECT_DIR"),
        str(HOME_DIR / "projects" / "hit-zone"),
        str(HOME_DIR / "projects" / "dcf-suite"),
        str(HOME_DIR / "codex-project"),
    ]
    for raw in candidates:
        text = str(raw or "").strip()
        if not text:
            continue
        root = Path(text).expanduser()
        data_dir = root / "data"
        if data_dir.exists():
            return data_dir
    return HOME_DIR / "projects" / "hit-zone" / "data"


HIT_ZONE_DATA_DIR = resolve_hit_zone_data_dir()
DEFAULT_TRUST_STANDARD = HIT_ZONE_DATA_DIR / "unified_trust_scoring_standard_v1.json"
DEFAULT_REVIEW_STANDARD = HIT_ZONE_DATA_DIR / "unified_review_workflow_standard_v1.json"
DEFAULT_FIELD_MAPPING = HIT_ZONE_DATA_DIR / "unified_field_source_mapping_v1.json"
DEFAULT_SOURCE_WHITELIST = HIT_ZONE_DATA_DIR / "unified_source_whitelist_and_applicability_v1.json"
DEFAULT_ANOMALY_STANDARD = HIT_ZONE_DATA_DIR / "unified_sampling_and_anomaly_standard_v1.json"
DEFAULT_BENCHMARK_MAPPING = HIT_ZONE_DATA_DIR / "unified_benchmark_mapping_v1.json"
DEFAULT_SNAPSHOT_ROOT = HOME_DIR / "projects" / "stock-data-hub" / "data_lake" / "snapshots"

FIELD_WEIGHTS: Dict[str, float] = {
    "focus_dashboard.price": 0.25,
    "focus_dashboard.fv50": 0.30,
    "opportunities.best_reason": 0.20,
    "benchmark.primary": 0.125,
    "benchmark.secondary": 0.125,
}


def parse_datetime(value: Any) -> datetime | None:
    text = normalize_text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.fromisoformat(f"{text[:10]}T00:00:00+00:00")
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return None


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


def load_contracts(
    *,
    trust_standard_file: Path = DEFAULT_TRUST_STANDARD,
    review_standard_file: Path = DEFAULT_REVIEW_STANDARD,
    field_mapping_file: Path = DEFAULT_FIELD_MAPPING,
    source_whitelist_file: Path = DEFAULT_SOURCE_WHITELIST,
    anomaly_standard_file: Path = DEFAULT_ANOMALY_STANDARD,
    benchmark_mapping_file: Path = DEFAULT_BENCHMARK_MAPPING,
) -> Dict[str, Any]:
    field_mapping_payload = read_json(field_mapping_file)
    field_rules = {
        normalize_text(item.get("field_id")): item
        for item in (field_mapping_payload.get("fields") or [])
        if isinstance(item, dict)
    }
    return {
        "trust_standard": read_json(trust_standard_file),
        "review_standard": read_json(review_standard_file),
        "field_rules": field_rules,
        "source_whitelist": read_json(source_whitelist_file),
        "anomaly_standard": read_json(anomaly_standard_file),
        "benchmark_mapping": read_json(benchmark_mapping_file),
    }


class SnapshotContext:
    def __init__(self, snapshot_root: Path | None = None, snapshot_date: str = "") -> None:
        self.snapshot_root = Path(snapshot_root) if snapshot_root else None
        self.snapshot_date = normalize_text(snapshot_date)
        self.snapshot_dir = self._resolve_snapshot_dir()
        self.price_history = self._load_jsonl_by_symbol(self.snapshot_dir / "price_history.jsonl") if self.snapshot_dir else {}

    def _resolve_snapshot_dir(self) -> Path | None:
        if self.snapshot_root is None or not self.snapshot_root.exists():
            return None
        if self.snapshot_date:
            direct = self.snapshot_root / f"dt={self.snapshot_date}"
            if direct.exists():
                return direct
        dirs = sorted(item for item in self.snapshot_root.glob("dt=*") if item.is_dir())
        if not dirs:
            return None
        return dirs[-1]

    def _load_jsonl_by_symbol(self, path: Path) -> Dict[str, Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}
        if not path.exists():
            return records
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except Exception:  # noqa: BLE001
                    continue
                if not isinstance(payload, dict):
                    continue
                symbol = normalize_text(payload.get("symbol")).upper()
                if symbol:
                    records[symbol] = payload
        return records

    def find_price_record(self, ticker: Any, symbol: Any) -> Dict[str, Any] | None:
        keys: List[str] = []
        for raw in [symbol, ticker, normalize_internal_symbol_for_ticker(ticker)]:
            for item in ticker_lookup_keys(raw):
                if item not in keys:
                    keys.append(item)
        for key in keys:
            payload = self.price_history.get(normalize_text(key).upper())
            if isinstance(payload, dict):
                return payload
        return None


def expected_primary_source(field_rule: Dict[str, Any], market: str) -> str:
    primary = field_rule.get("primary_source")
    if isinstance(primary, dict):
        return normalize_text(primary.get(normalize_text(market).upper()))
    return normalize_text(primary)


def expected_backup_sources(field_rule: Dict[str, Any], market: str) -> List[str]:
    payload = field_rule.get("backup_sources")
    if isinstance(payload, dict):
        values = payload.get(normalize_text(market).upper()) or []
    else:
        values = payload or []
    return [normalize_text(item) for item in values if normalize_text(item)]


def expected_reference_sources(field_rule: Dict[str, Any]) -> List[str]:
    return [normalize_text(item) for item in (field_rule.get("reference_sources") or []) if normalize_text(item)]


def provider_tier(provider: str, domain: str, market: str, whitelist: Dict[str, Any]) -> str:
    provider_name = normalize_text(provider)
    if not provider_name:
        return "UNKNOWN"
    domains = whitelist.get("domains") or {}
    domain_payload = domains.get(domain) or {}
    if domain == "quote_data":
        market_payload = domain_payload.get(normalize_text(market).upper()) or {}
        for tier_id in ["P1", "P2", "P3"]:
            if provider_name in [normalize_text(item) for item in (market_payload.get(tier_id) or [])]:
                return tier_id
        return "UNKNOWN"
    for tier_id in ["P1", "P2", "P3"]:
        if provider_name in [normalize_text(item) for item in (domain_payload.get(tier_id) or [])]:
            return tier_id
    return "UNKNOWN"


def score_traceability(lineage: Dict[str, Any], trust_standard: Dict[str, Any]) -> float:
    subscores = (((trust_standard.get("dimensions") or {}).get("traceability") or {}).get("subscores") or {})
    total = 0.0
    for key, points in subscores.items():
        value = lineage.get(key)
        if key == "cache_ttl" and value is not None:
            total += float(points)
        elif normalize_text(value):
            total += float(points)
    return total


def score_freshness(updated_at: Any, reference_dt: datetime | None, sla_hours: float | None) -> tuple[float, float | None]:
    updated_dt = parse_datetime(updated_at)
    if updated_dt is None or reference_dt is None or sla_hours is None or sla_hours <= 0:
        return 0.0, None
    age_hours = max(0.0, (reference_dt - updated_dt).total_seconds() / 3600.0)
    if age_hours <= 1.0 * sla_hours:
        return 100.0, age_hours
    if age_hours <= 1.5 * sla_hours:
        return 85.0, age_hours
    if age_hours <= 2.0 * sla_hours:
        return 70.0, age_hours
    if age_hours <= 3.0 * sla_hours:
        return 50.0, age_hours
    return 20.0, age_hours


def match_type(observed_provider: str, primary: str, backups: Sequence[str], references: Sequence[str], *, force_reference_only: bool = False) -> str:
    provider = normalize_text(observed_provider)
    if force_reference_only:
        return "reference_only"
    if provider and provider == primary:
        return "primary"
    if provider and provider in backups:
        return "backup"
    if provider and provider in references:
        return "reference"
    if not provider:
        return "unknown"
    return "custom"


def source_authenticity_score(observed_provider: str, observed_source_system: str, source_match: str, truth_level: str) -> float:
    provider = normalize_text(observed_provider)
    source_system = normalize_text(observed_source_system)
    if truth_level == "fallback_only" or source_match in {"reference_only", "clue_only"}:
        return 45.0
    if source_system == "benchmark_mapping_formal_asset":
        return 100.0
    if provider in {"local_verified_cache"}:
        return 100.0
    if source_system.startswith("snapshot"):
        return 100.0
    if provider in {
        "local_dcf_snapshot",
        "dcf_engine_result_cache",
        "method_decision_trace",
        "opportunity_csv_snapshot",
        "external_valuation_cache",
        "stock_data_hub",
        "stock_data_hub_comps_baseline",
    }:
        return 92.0
    if provider in {"yahoo_finance", "yahoo_target_mean_price", "fmp", "alpha_vantage", "yfinance"}:
        return 75.0
    if provider in {"close_fallback", "heuristic_fallback"}:
        return 45.0
    if source_match == "primary":
        return 92.0
    if source_match == "backup":
        return 75.0
    if source_match == "reference":
        return 65.0
    return 0.0


def consistency_score_for_field(field_id: str, signal: Dict[str, Any], position: Dict[str, Any], source_match: str) -> float:
    if field_id == "focus_dashboard.price":
        if source_match in {"primary", "backup", "custom"}:
            return 85.0
        if source_match == "reference":
            return 65.0
        return 40.0
    if field_id == "focus_dashboard.fv50":
        valuation_source = normalize_text(signal.get("valuation_source_at_signal"))
        if valuation_source == "dcf_iv_base":
            return 85.0
        if valuation_source == "target_mean_price":
            return 65.0
        if valuation_source == "close_fallback":
            return 40.0
        return 50.0
    if field_id == "opportunities.best_reason":
        trace_summary = signal.get("trace_summary") or {}
        if normalize_text(signal.get("entry_reason_summary")) and not (trace_summary.get("hard_fail_reasons") or []):
            return 100.0
        if normalize_text(signal.get("entry_reason_summary")):
            return 75.0
        return 0.0
    if field_id.startswith("benchmark."):
        return 100.0 if normalize_text((signal.get(field_id.split(".")[-1] + "_benchmark") or {}).get("benchmark_id")) else 75.0
    status = normalize_text(position.get("status"))
    return 75.0 if status else 0.0


def grade_from_score(score: float) -> str:
    if score >= 95:
        return "A"
    if score >= 90:
        return "B"
    if score >= 75:
        return "C"
    return "D"


def label_from_grade(grade: str) -> str:
    return {
        "A": "主参考",
        "B": "辅助参考",
        "C": "仅参考",
        "D": "不可正式使用",
    }.get(grade, "不可正式使用")


def max_grade(grade_a: str, grade_b: str) -> str:
    order = {"A": 0, "B": 1, "C": 2, "D": 3}
    return grade_a if order.get(grade_a, 3) >= order.get(grade_b, 3) else grade_b


def reference_datetime_for_signal(signal: Dict[str, Any], position: Dict[str, Any]) -> datetime | None:
    candidate = normalize_text(position.get("validation_as_of_date")) or normalize_text(signal.get("as_of_date"))
    if not candidate:
        return None
    return parse_datetime(f"{candidate}T23:59:59+00:00")


def build_lineage_row(
    *,
    signal: Dict[str, Any],
    position: Dict[str, Any],
    field_id: str,
    label: str,
    domain: str,
    market: str,
    value_at_signal: Any,
    observed_source_system: str,
    source_file_or_api: str,
    observed_provider: str,
    updated_at: str,
    cache_ttl: float | None,
    verified_status: str,
    truth_level: str,
    freshness_sla_hours: float | None,
    cross_check_rule: str,
    expected_primary: str,
    expected_backups: Sequence[str],
    expected_references: Sequence[str],
    force_reference_only: bool,
    trust_standard: Dict[str, Any],
    whitelist: Dict[str, Any],
) -> Dict[str, Any]:
    source_match = match_type(
        observed_provider,
        expected_primary,
        expected_backups,
        expected_references,
        force_reference_only=force_reference_only,
    )
    reference_dt = reference_datetime_for_signal(signal, position)
    freshness_score, age_hours = score_freshness(updated_at, reference_dt, freshness_sla_hours)
    observed_provider_tier = provider_tier(observed_provider, domain, market, whitelist)
    row = {
        "signal_id": normalize_text(signal.get("signal_id")),
        "ticker": normalize_text(signal.get("ticker")),
        "name": normalize_text(signal.get("name")),
        "market": market,
        "field_id": field_id,
        "field_label": label,
        "domain": domain,
        "value_at_signal": value_at_signal,
        "source_system": observed_source_system,
        "source_file_or_api": source_file_or_api,
        "observed_provider": observed_provider,
        "observed_provider_tier": observed_provider_tier,
        "updated_at": updated_at,
        "cache_ttl": cache_ttl,
        "verified_status": verified_status,
        "truth_level": truth_level,
        "freshness_sla_hours": freshness_sla_hours,
        "age_hours_vs_reference": age_hours,
        "cross_check_rule": cross_check_rule,
        "expected_primary_source": expected_primary,
        "expected_backup_sources": list(expected_backups),
        "expected_reference_sources": list(expected_references),
        "source_match_type": source_match,
    }
    row["source_authenticity_score"] = source_authenticity_score(observed_provider, observed_source_system, source_match, truth_level)
    row["traceability_score"] = score_traceability(row, trust_standard)
    row["freshness_score"] = freshness_score
    row["consistency_score"] = consistency_score_for_field(field_id, signal, position, source_match)
    row["warnings"] = []
    row["hard_veto_flags"] = []
    if not normalize_text(row.get("source_system")) or not normalize_text(row.get("source_file_or_api")):
        row["hard_veto_flags"].append("H1_source_unknown")
    if truth_level == "fallback_only":
        row["hard_veto_flags"].append("H2_inferred_or_fallback_only")
    if age_hours is not None and freshness_sla_hours and age_hours > 3.0 * freshness_sla_hours:
        row["hard_veto_flags"].append("H4_severely_stale")
    if source_match in {"reference", "reference_only", "custom", "unknown"}:
        row["warnings"].append(f"source_match={source_match}")
    if freshness_score < 85:
        row["warnings"].append("freshness_below_target")
    if row["consistency_score"] < 85:
        row["warnings"].append("cross_source_consistency_weakened")
    return row


def build_field_lineage_rows(
    signal: Dict[str, Any],
    position: Dict[str, Any],
    contracts: Dict[str, Any],
    snapshot_context: SnapshotContext,
) -> List[Dict[str, Any]]:
    whitelist = contracts["source_whitelist"]
    trust_standard = contracts["trust_standard"]
    field_rules = contracts["field_rules"]
    benchmark_mapping = contracts["benchmark_mapping"]
    artifacts = ((signal.get("snapshot_refs") or {}).get("artifacts") or [])
    artifact_by_kind = {normalize_text(item.get("kind")): item for item in artifacts if isinstance(item, dict)}
    market = normalize_text(signal.get("market")) or normalize_text(position.get("market")) or "US"
    meta_generated = normalize_text((((signal.get("snapshot_refs") or {}).get("meta_ref") or {}).get("generated_at_utc")))
    snapshot_record = snapshot_context.find_price_record(signal.get("ticker"), signal.get("symbol"))
    snapshot_provider = normalize_text((snapshot_record or {}).get("provider")) or "local_verified_cache"
    snapshot_source_chain = (snapshot_record or {}).get("source_chain") or []
    price_source = normalize_text(position.get("price_history_source"))
    if price_source.startswith("snapshot:"):
        price_system = "snapshot_price_history"
        price_provider = "local_verified_cache"
        price_file = str((snapshot_context.snapshot_dir / "price_history.jsonl") if snapshot_context.snapshot_dir else "")
        price_updated_at = normalize_text((snapshot_record or {}).get("as_of")) or meta_generated or normalize_text(signal.get("signal_generated_at_utc"))
        price_truth_level = "formal_snapshot"
    elif price_source.startswith("stock_data_hub:"):
        price_system = "stock_data_hub"
        price_provider = "local_verified_cache"
        price_file = "stock_data_hub:/v1/price-history"
        price_updated_at = normalize_text(position.get("validation_as_of_date")) or meta_generated
        price_truth_level = "formal_cached"
    elif price_source.startswith("yfinance:"):
        price_system = "yfinance"
        price_provider = "yfinance"
        price_file = "yfinance.Ticker.history"
        price_updated_at = normalize_text(position.get("validation_as_of_date")) or meta_generated
        price_truth_level = "single_external"
    else:
        price_system = "opportunity_real_snapshot"
        price_provider = "local_verified_cache"
        price_file = normalize_text((artifact_by_kind.get("real_file") or {}).get("path"))
        price_updated_at = meta_generated or normalize_text(signal.get("signal_generated_at_utc"))
        price_truth_level = "formal_snapshot"

    price_rule = field_rules.get("focus_dashboard.price") or {}
    valuation_rule = field_rules.get("focus_dashboard.fv50") or {}
    reason_rule = field_rules.get("opportunities.best_reason") or {}
    rows = [
        build_lineage_row(
            signal=signal,
            position=position,
            field_id="focus_dashboard.price",
            label=normalize_text(price_rule.get("label")) or "当前价",
            domain=normalize_text(price_rule.get("domain")) or "quote_data",
            market=market,
            value_at_signal=as_float(signal.get("price_at_signal")),
            observed_source_system=price_system,
            source_file_or_api=price_file,
            observed_provider=price_provider,
            updated_at=price_updated_at,
            cache_ttl=as_float(price_rule.get("freshness_sla_hours")) or 24.0,
            verified_status="verified" if normalize_text(signal.get("review_state")) == "auto" else "warning",
            truth_level=price_truth_level,
            freshness_sla_hours=as_float(price_rule.get("freshness_sla_hours")) or 24.0,
            cross_check_rule=normalize_text(price_rule.get("cross_check_rule")) or "price_or_valuation",
            expected_primary=expected_primary_source(price_rule, market),
            expected_backups=expected_backup_sources(price_rule, market),
            expected_references=expected_reference_sources(price_rule),
            force_reference_only=False,
            trust_standard=trust_standard,
            whitelist=whitelist,
        )
    ]

    valuation_source = normalize_text(signal.get("valuation_source_at_signal"))
    valuation_detail = normalize_text(signal.get("valuation_source_detail_at_signal"))
    valuation_system = "valuation_snapshot"
    valuation_provider = "unknown"
    valuation_truth = "formal_snapshot"
    force_reference_only = False
    if valuation_source == "dcf_iv_base":
        valuation_provider = "local_dcf_snapshot"
    elif valuation_source == "target_mean_price":
        valuation_provider = "external_valuation_cache"
        valuation_truth = "reference_snapshot"
        force_reference_only = True
    elif valuation_source == "dcf_external_consensus":
        valuation_provider = "external_valuation_cache"
        valuation_truth = "reference_snapshot"
        force_reference_only = True
    elif valuation_source == "close_fallback":
        valuation_provider = "close_fallback"
        valuation_truth = "fallback_only"
        force_reference_only = True
    if "yahoo_target_mean_price" in valuation_detail:
        valuation_system = "yahoo_target_mean_price"
    elif valuation_provider == "local_dcf_snapshot":
        valuation_system = "local_dcf_snapshot"
    rows.append(
        build_lineage_row(
            signal=signal,
            position=position,
            field_id="focus_dashboard.fv50",
            label=normalize_text(valuation_rule.get("label")) or "中性估值",
            domain=normalize_text(valuation_rule.get("domain")) or "valuation",
            market=market,
            value_at_signal=as_float(signal.get("fair_value_at_signal")),
            observed_source_system=valuation_system,
            source_file_or_api=normalize_text((artifact_by_kind.get("real_file") or {}).get("path")) or valuation_detail,
            observed_provider=valuation_provider,
            updated_at=meta_generated or normalize_text(signal.get("signal_generated_at_utc")),
            cache_ttl=as_float(valuation_rule.get("freshness_sla_hours")) or 24.0,
            verified_status="verified" if normalize_text(signal.get("review_state")) == "auto" else "needs_review",
            truth_level=valuation_truth,
            freshness_sla_hours=as_float(valuation_rule.get("freshness_sla_hours")) or 24.0,
            cross_check_rule=normalize_text(valuation_rule.get("cross_check_rule")) or "multiple_or_financial",
            expected_primary=expected_primary_source(valuation_rule, market),
            expected_backups=expected_backup_sources(valuation_rule, market),
            expected_references=expected_reference_sources(valuation_rule),
            force_reference_only=force_reference_only,
            trust_standard=trust_standard,
            whitelist=whitelist,
        )
    )

    rows.append(
        build_lineage_row(
            signal=signal,
            position=position,
            field_id="opportunities.best_reason",
            label=normalize_text(reason_rule.get("label")) or "机会原因",
            domain=normalize_text(reason_rule.get("domain")) or "opportunity_generation",
            market=market,
            value_at_signal=normalize_text(signal.get("entry_reason_summary")),
            observed_source_system="method_decision_trace",
            source_file_or_api=normalize_text((artifact_by_kind.get("trace_file") or {}).get("path")),
            observed_provider="method_decision_trace",
            updated_at=meta_generated or normalize_text(signal.get("signal_generated_at_utc")),
            cache_ttl=as_float(reason_rule.get("freshness_sla_hours")) or 24.0,
            verified_status="verified",
            truth_level="formal_generated",
            freshness_sla_hours=as_float(reason_rule.get("freshness_sla_hours")) or 24.0,
            cross_check_rule=normalize_text(reason_rule.get("cross_check_rule")) or "non_empty_and_consistent_method_id",
            expected_primary=expected_primary_source(reason_rule, market),
            expected_backups=expected_backup_sources(reason_rule, market),
            expected_references=expected_reference_sources(reason_rule),
            force_reference_only=False,
            trust_standard=trust_standard,
            whitelist=whitelist,
        )
    )

    benchmark_file = str(DEFAULT_BENCHMARK_MAPPING if DEFAULT_BENCHMARK_MAPPING.exists() else "")
    for field_id, payload in [
        ("benchmark.primary", signal.get("primary_benchmark") or {}),
        ("benchmark.secondary", signal.get("secondary_benchmark") or {}),
    ]:
        rows.append(
            build_lineage_row(
                signal=signal,
                position=position,
                field_id=field_id,
                label="一级基准" if field_id.endswith("primary") else "二级基准",
                domain="quote_data",
                market=market,
                value_at_signal=normalize_text(payload.get("benchmark_id")),
                observed_source_system="benchmark_mapping_formal_asset",
                source_file_or_api=benchmark_file,
                observed_provider="local_verified_cache",
                updated_at=normalize_text(signal.get("signal_generated_at_utc")) or meta_generated,
                cache_ttl=168.0,
                verified_status="verified",
                truth_level="formal_policy",
                freshness_sla_hours=168.0,
                cross_check_rule="benchmark_mapping",
                expected_primary="local_verified_cache",
                expected_backups=[],
                expected_references=[],
                force_reference_only=False,
                trust_standard=trust_standard,
                whitelist=whitelist,
            )
        )
    return rows


def summarize_validation_slice(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    evaluated = [row for row in rows if normalize_text(row.get("status")) != "pending_entry"]
    returns = [as_float(row.get("strategy_return_net")) for row in evaluated if as_float(row.get("strategy_return_net")) is not None]
    excess = [as_float(row.get("primary_excess_return")) for row in evaluated if as_float(row.get("primary_excess_return")) is not None]
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
        "hit_rate": (sum(1.0 for item in hits if item) / len(hits)) if hits else None,
    }


def opportunity_score(
    signal: Dict[str, Any],
    position: Dict[str, Any],
    field_rows: Sequence[Dict[str, Any]],
    contracts: Dict[str, Any],
) -> Dict[str, Any]:
    trust_standard = contracts["trust_standard"]
    review_standard = contracts["review_standard"]
    anomaly_standard = contracts["anomaly_standard"]
    weighted_source = 0.0
    weighted_trace = 0.0
    weighted_consistency = 0.0
    weighted_freshness = 0.0
    total_weight = 0.0
    hard_veto_reasons: List[str] = []
    warnings: List[str] = []
    field_grade_caps: List[str] = []
    for row in field_rows:
        weight = FIELD_WEIGHTS.get(normalize_text(row.get("field_id")), 0.0)
        total_weight += weight
        weighted_source += weight * float(row.get("source_authenticity_score") or 0.0)
        weighted_trace += weight * float(row.get("traceability_score") or 0.0)
        weighted_consistency += weight * float(row.get("consistency_score") or 0.0)
        weighted_freshness += weight * float(row.get("freshness_score") or 0.0)
        hard_veto_reasons.extend(normalize_text(item) for item in (row.get("hard_veto_flags") or []) if normalize_text(item))
        warnings.extend(normalize_text(item) for item in (row.get("warnings") or []) if normalize_text(item))
        if normalize_text(row.get("field_id")) == "focus_dashboard.fv50":
            if normalize_text(row.get("source_match_type")) == "reference_only":
                field_grade_caps.append("C")
            if normalize_text(row.get("truth_level")) == "fallback_only":
                field_grade_caps.append("D")
    total_weight = total_weight or 1.0
    source_score = weighted_source / total_weight
    trace_score = weighted_trace / total_weight
    consistency_score = weighted_consistency / total_weight
    freshness_score = weighted_freshness / total_weight
    weights = ((trust_standard.get("formula") or {}).get("weights") or {})
    trust_score = (
        float(weights.get("source_authenticity") or 0.4) * source_score
        + float(weights.get("traceability") or 0.25) * trace_score
        + float(weights.get("cross_source_consistency") or 0.2) * consistency_score
        + float(weights.get("freshness") or 0.15) * freshness_score
    )
    review_state = normalize_text(signal.get("review_state"))
    review_reason = normalize_text(signal.get("review_reason"))
    position_status = normalize_text(position.get("status"))
    valuation_source = normalize_text(signal.get("valuation_source_at_signal"))
    if valuation_source == "close_fallback":
        hard_veto_reasons.append("H2_inferred_or_fallback_only")
        trust_score = min(trust_score, 59.0)
    if any(reason.startswith("H4") for reason in hard_veto_reasons):
        trust_score = min(trust_score, 69.0)
    if any(reason.startswith("H5") for reason in hard_veto_reasons):
        trust_score = min(trust_score, 49.0)
    raw_grade = grade_from_score(trust_score)
    final_grade = raw_grade
    for cap in field_grade_caps:
        final_grade = max_grade(final_grade, cap)
    if hard_veto_reasons:
        final_grade = "D"
    review_checks = {
        "R0": {
            "required_fields_present": all(
                [
                    normalize_text(signal.get("ticker")),
                    normalize_text(signal.get("as_of_date")),
                    normalize_text(signal.get("method_group_id")),
                    normalize_text(signal.get("entry_reason_summary")),
                    signal.get("price_at_signal") is not None,
                    normalize_text(signal.get("valuation_source_at_signal")),
                    normalize_text(signal.get("exit_template_id")),
                ]
            ),
            "time_fields_parseable": bool(reference_datetime_for_signal(signal, position)),
            "symbol_market_mappable": bool(normalize_text(signal.get("symbol")) or normalize_text(signal.get("ticker"))),
        },
        "R1": {
            "source_system_present": all(normalize_text(row.get("source_system")) for row in field_rows),
            "source_file_or_api_present": all(normalize_text(row.get("source_file_or_api")) for row in field_rows),
            "updated_at_present": all(normalize_text(row.get("updated_at")) for row in field_rows),
            "cache_ttl_present": all(row.get("cache_ttl") is not None for row in field_rows),
            "verified_status_present": all(normalize_text(row.get("verified_status")) for row in field_rows),
            "truth_level_present": all(normalize_text(row.get("truth_level")) for row in field_rows),
            "age_within_sla": all(float(row.get("freshness_score") or 0.0) >= 70.0 for row in field_rows),
        },
        "R2": {
            "numeric_tolerance_check": all(float(row.get("consistency_score") or 0.0) >= 40.0 for row in field_rows),
            "primary_backup_alignment": all(normalize_text(row.get("source_match_type")) not in {"unknown"} for row in field_rows),
            "single_source_downgrade": any(normalize_text(row.get("source_match_type")) in {"reference", "reference_only", "custom"} for row in field_rows),
            "conflict_explanation_present": not review_reason or review_state in {"escalated", "blocked"},
        },
        "R3": {
            "entity_alignment_check": bool(normalize_text(signal.get("ticker")) and normalize_text(signal.get("name"))),
            "dcf_quality_gate_check": review_state != "blocked",
            "execution_rule_presence_check": bool(normalize_text(signal.get("exit_template_id")) and normalize_text(signal.get("entry_reason_summary"))),
        },
    }
    if not all(review_checks["R0"].values()) or not all(
        review_checks["R1"][key]
        for key in [
            "source_system_present",
            "source_file_or_api_present",
            "updated_at_present",
            "cache_ttl_present",
            "verified_status_present",
            "truth_level_present",
        ]
    ):
        review_result = "auto_reject"
    elif review_state == "blocked":
        review_result = "auto_reject"
    elif review_state == "escalated":
        review_result = "manual_escalation"
    elif position_status == "pending_entry":
        review_result = "auto_hold"
    elif warnings:
        review_result = "auto_pass_with_warning"
    else:
        review_result = "auto_pass"

    trigger_counts = anomaly_standard.get("auto_escalation_triggers") or []
    escalation_triggers: List[str] = []
    if review_state == "escalated":
        escalation_triggers.append("high_grade_source_conflict")
    if any(reason.startswith("H2") for reason in hard_veto_reasons):
        escalation_triggers.append("cross_module_field_inconsistency")
    if any(reason.startswith("H4") for reason in hard_veto_reasons):
        escalation_triggers.append("trust_score_abrupt_jump")
    escalation_triggers = [item for item in escalation_triggers if item in trigger_counts or item]

    trust_bucket = "high_confidence"
    if final_grade == "C" or review_result == "auto_hold":
        trust_bucket = "watch"
    if final_grade == "D" or review_result in {"manual_escalation", "auto_reject"}:
        trust_bucket = "noisy"
    formal_layer = final_grade in {"A", "B"} and review_result in {"auto_pass", "auto_pass_with_warning"}
    suggested_action = {
        "high_confidence": "keep_in_formal_layer",
        "watch": "keep_in_watch_pool",
        "noisy": "send_to_review_queue",
    }[trust_bucket]
    priority = "P3"
    if trust_bucket == "noisy":
        priority = "P1"
    elif trust_bucket == "watch":
        priority = "P2"

    return {
        "signal_id": normalize_text(signal.get("signal_id")),
        "ticker": normalize_text(signal.get("ticker")),
        "name": normalize_text(signal.get("name")),
        "market": normalize_text(signal.get("market")),
        "method_group": normalize_text(signal.get("method_group")),
        "method_group_id": normalize_text(signal.get("method_group_id")),
        "valuation_source_at_signal": valuation_source,
        "review_state": review_state,
        "review_reason": review_reason,
        "position_status": position_status,
        "trust_score": round(trust_score, 2),
        "trust_grade": final_grade,
        "trust_label": label_from_grade(final_grade),
        "trust_bucket": trust_bucket,
        "formal_layer_eligible": formal_layer,
        "review_result": review_result,
        "review_layers": review_checks,
        "escalation_triggers": escalation_triggers,
        "priority": priority,
        "suggested_action": suggested_action,
        "hard_veto_reasons": sorted(set(hard_veto_reasons)),
        "warnings": sorted(set(warnings)),
        "trust_breakdown": {
            "source_authenticity": round(source_score, 2),
            "traceability": round(trace_score, 2),
            "cross_source_consistency": round(consistency_score, 2),
            "freshness": round(freshness_score, 2),
        },
        "validation_snapshot": {
            "status": position_status,
            "primary_excess_return": as_float(position.get("primary_excess_return")),
            "strategy_return_net": as_float(position.get("strategy_return_net")),
            "days_held": position.get("days_held"),
        },
        "standards_applied": {
            "trust_standard": normalize_text(contracts["trust_standard"].get("purpose")),
            "review_standard": normalize_text(review_standard.get("purpose")),
        },
    }


def build_review_item(signal: Dict[str, Any], position: Dict[str, Any], score_row: Dict[str, Any]) -> Dict[str, Any]:
    reasons = list(score_row.get("hard_veto_reasons") or []) + list(score_row.get("warnings") or []) + list(score_row.get("escalation_triggers") or [])
    if normalize_text(score_row.get("review_reason")):
        reasons.append(normalize_text(score_row.get("review_reason")))
    return {
        "signal_id": score_row.get("signal_id"),
        "ticker": score_row.get("ticker"),
        "name": score_row.get("name"),
        "market": score_row.get("market"),
        "method_group": score_row.get("method_group"),
        "priority": score_row.get("priority"),
        "trust_bucket": score_row.get("trust_bucket"),
        "trust_grade": score_row.get("trust_grade"),
        "trust_score": score_row.get("trust_score"),
        "review_result": score_row.get("review_result"),
        "position_status": score_row.get("position_status"),
        "queue_reason_summary": sorted({normalize_text(item) for item in reasons if normalize_text(item)}),
        "suggested_action": score_row.get("suggested_action"),
        "as_of_date": normalize_text(signal.get("as_of_date")),
        "validation_as_of_date": normalize_text(position.get("validation_as_of_date")),
    }


def build_trust_outputs(
    *,
    signals: Sequence[Dict[str, Any]],
    positions: Sequence[Dict[str, Any]],
    contracts: Dict[str, Any],
    snapshot_root: Path | None = DEFAULT_SNAPSHOT_ROOT,
    snapshot_date: str = "",
) -> Dict[str, Any]:
    snapshot_context = SnapshotContext(snapshot_root=snapshot_root, snapshot_date=snapshot_date)
    positions_by_signal = {normalize_text(item.get("signal_id")): item for item in positions if isinstance(item, dict)}
    field_lineage_rows: List[Dict[str, Any]] = []
    score_rows: List[Dict[str, Any]] = []
    review_items: List[Dict[str, Any]] = []
    grouped_validation_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for signal in signals:
        signal_id = normalize_text(signal.get("signal_id"))
        position = positions_by_signal.get(signal_id, {})
        field_rows = build_field_lineage_rows(signal, position, contracts, snapshot_context)
        field_lineage_rows.extend(field_rows)
        score_row = opportunity_score(signal, position, field_rows, contracts)
        score_rows.append(score_row)
        grouped_validation_rows[normalize_text(score_row.get("trust_bucket"))].append(position)
        if normalize_text(score_row.get("trust_bucket")) != "high_confidence" or normalize_text(score_row.get("review_result")) != "auto_pass":
            review_items.append(build_review_item(signal, position, score_row))

    score_rows.sort(key=lambda item: ({"high_confidence": 0, "watch": 1, "noisy": 2}.get(normalize_text(item.get("trust_bucket")), 9), -(item.get("trust_score") or 0), normalize_text(item.get("ticker"))))
    review_items.sort(key=lambda item: ({"P1": 0, "P2": 1, "P3": 2}.get(normalize_text(item.get("priority")), 9), normalize_text(item.get("ticker"))))
    provider_tier_breakdown = Counter(normalize_text(row.get("observed_provider_tier")) or "UNKNOWN" for row in field_lineage_rows)
    source_match_breakdown = Counter(normalize_text(row.get("source_match_type")) or "unknown" for row in field_lineage_rows)
    field_traceability_rate = (
        sum(1 for row in field_lineage_rows if normalize_text(row.get("source_system")) and normalize_text(row.get("source_file_or_api")))
        / len(field_lineage_rows)
        if field_lineage_rows else 0.0
    )
    validation_by_bucket = {
        bucket: summarize_validation_slice(rows)
        for bucket, rows in sorted(grouped_validation_rows.items())
    }
    confidence_doc = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_context": {
            "snapshot_root": str(snapshot_root or ""),
            "snapshot_dir": str(snapshot_context.snapshot_dir or ""),
        },
        "total_opportunities": len(score_rows),
        "trust_bucket_breakdown": dict(Counter(normalize_text(row.get("trust_bucket")) for row in score_rows)),
        "trust_grade_breakdown": dict(Counter(normalize_text(row.get("trust_grade")) for row in score_rows)),
        "review_result_breakdown": dict(Counter(normalize_text(row.get("review_result")) for row in score_rows)),
        "formal_layer_breakdown": {
            "formal": sum(1 for row in score_rows if row.get("formal_layer_eligible")),
            "non_formal": sum(1 for row in score_rows if not row.get("formal_layer_eligible")),
        },
        "validation_by_confidence_bucket": validation_by_bucket,
        "top_risk_patterns": dict(Counter(reason for row in score_rows for reason in (row.get("hard_veto_reasons") or []) + (row.get("warnings") or []))),
        "opportunities": score_rows,
    }
    lineage_doc = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_context": confidence_doc["snapshot_context"],
        "total_opportunities": len(score_rows),
        "total_field_rows": len(field_lineage_rows),
        "field_traceability_rate": round(field_traceability_rate, 4),
        "provider_tier_breakdown": dict(provider_tier_breakdown),
        "source_match_breakdown": dict(source_match_breakdown),
        "fields": field_lineage_rows,
    }
    review_doc = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_items": len(review_items),
        "priority_breakdown": dict(Counter(normalize_text(row.get("priority")) for row in review_items)),
        "review_result_breakdown": dict(Counter(normalize_text(row.get("review_result")) for row in review_items)),
        "trust_bucket_breakdown": dict(Counter(normalize_text(row.get("trust_bucket")) for row in review_items)),
        "queue_items": review_items,
    }
    return {
        "lineage": lineage_doc,
        "confidence": confidence_doc,
        "review_queue": review_doc,
    }


def render_confidence_markdown(confidence_doc: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# 机会可信度最新报表")
    lines.append("")
    lines.append(f"- 生成时间：{normalize_text(confidence_doc.get('generated_at_utc'))}")
    lines.append(f"- 总机会数：{confidence_doc.get('total_opportunities', 0)}")
    snapshot_context = confidence_doc.get("snapshot_context") or {}
    lines.append(f"- Snapshot：`{normalize_text(snapshot_context.get('snapshot_dir')) or '-'}`")
    lines.append("")
    lines.append("## 分层分布")
    lines.append("")
    lines.append(f"- 可信度分层：`{json.dumps(confidence_doc.get('trust_bucket_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 等级分布：`{json.dumps(confidence_doc.get('trust_grade_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 复核结果：`{json.dumps(confidence_doc.get('review_result_breakdown') or {}, ensure_ascii=False)}`")
    lines.append("")
    lines.append("## 验真分层")
    lines.append("")
    lines.append("| 分层 | 样本 | 已评估 | Open | Closed | Expired | Pending | 平均净收益 | 一级超额 | 命中率 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for bucket, row in sorted((confidence_doc.get('validation_by_confidence_bucket') or {}).items()):
        lines.append(
            "| {bucket} | {count} | {evaluated} | {open_count} | {closed_count} | {expired_count} | {pending_count} | {avg_return} | {avg_excess} | {hit_rate} |".format(
                bucket=bucket,
                count=row.get("count", 0),
                evaluated=row.get("evaluated_count", 0),
                open_count=row.get("open_count", 0),
                closed_count=row.get("closed_count", 0),
                expired_count=row.get("expired_count", 0),
                pending_count=row.get("pending_entry_count", 0),
                avg_return=_fmt_pct(row.get("avg_strategy_return_net")),
                avg_excess=_fmt_pct(row.get("avg_primary_excess_return")),
                hit_rate=_fmt_pct(row.get("hit_rate")),
            )
        )
    lines.append("")
    lines.append("## 机会明细")
    lines.append("")
    lines.append("| 标的 | 分层 | 等级 | 复核结果 | 状态 | 估值来源 | 分数 | 主要问题 |")
    lines.append("|---|---|---|---|---|---|---:|---|")
    for row in confidence_doc.get("opportunities") or []:
        issues = ", ".join((row.get("hard_veto_reasons") or [])[:2] + (row.get("warnings") or [])[:1])
        lines.append(
            "| {name}({ticker}) | {bucket} | {grade} | {review_result} | {status} | {valuation_source} | {score} | {issues} |".format(
                name=normalize_text(row.get("name")),
                ticker=normalize_text(row.get("ticker")),
                bucket=normalize_text(row.get("trust_bucket")),
                grade=normalize_text(row.get("trust_grade")),
                review_result=normalize_text(row.get("review_result")),
                status=normalize_text((row.get("validation_snapshot") or {}).get("status")),
                valuation_source=normalize_text(row.get("valuation_source_at_signal")),
                score=normalize_text(row.get("trust_score")),
                issues=issues or "-",
            )
        )
    return "\n".join(lines) + "\n"


def render_review_queue_markdown(review_doc: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# 机会复核队列最新报表")
    lines.append("")
    lines.append(f"- 生成时间：{normalize_text(review_doc.get('generated_at_utc'))}")
    lines.append(f"- 队列条数：{review_doc.get('total_items', 0)}")
    lines.append(f"- 优先级：`{json.dumps(review_doc.get('priority_breakdown') or {}, ensure_ascii=False)}`")
    lines.append("")
    lines.append("| 优先级 | 标的 | 分层 | 等级 | 复核结果 | 状态 | 建议动作 | 原因 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in review_doc.get("queue_items") or []:
        lines.append(
            "| {priority} | {name}({ticker}) | {bucket} | {grade} | {review_result} | {status} | {action} | {reasons} |".format(
                priority=normalize_text(row.get("priority")),
                name=normalize_text(row.get("name")),
                ticker=normalize_text(row.get("ticker")),
                bucket=normalize_text(row.get("trust_bucket")),
                grade=normalize_text(row.get("trust_grade")),
                review_result=normalize_text(row.get("review_result")),
                status=normalize_text(row.get("position_status")),
                action=normalize_text(row.get("suggested_action")),
                reasons=", ".join(row.get("queue_reason_summary") or []) or "-",
            )
        )
    return "\n".join(lines) + "\n"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.2f}%"


def load_validation_positions(path: Path) -> List[Dict[str, Any]]:
    payload = read_json(path)
    return [item for item in (payload.get("positions") or []) if isinstance(item, dict)]
