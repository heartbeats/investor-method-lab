from __future__ import annotations

import csv
import os
import sys
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from investor_method_lab.opportunity_validation import valuation_support_tier
from investor_method_lab.signal_ledger import load_ledger_entries, normalize_text


def optional_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == '':
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_market(ticker: Any, explicit_market: Any = "") -> str:
    market = normalize_text(explicit_market).upper()
    if market in {"A", "HK", "US"}:
        return market
    value = normalize_text(ticker).upper()
    if value.endswith((".SS", ".SZ")) or value[:2] in {"SH", "SZ"}:
        return "A"
    if value.endswith(".HK") or value.startswith("HK."):
        return "HK"
    return "US"


def load_real_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            rows.append(dict(row))
    return rows


def real_lookup(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {normalize_text(row.get("ticker")): dict(row) for row in rows if normalize_text(row.get("ticker"))}


def signal_lookup(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {normalize_text(row.get("ticker")): dict(row) for row in rows if normalize_text(row.get("ticker"))}


def to_dcf_symbol(ticker: Any) -> str:
    raw = normalize_text(ticker).upper()
    if raw.endswith('.SS'):
        return f"SH.{raw[:-3]}"
    if raw.endswith('.SZ'):
        return f"SZ.{raw[:-3]}"
    if raw.endswith('.HK'):
        code = raw[:-3]
        return f"HK.{code.zfill(5)}" if code.isdigit() else f"HK.{code}"
    if raw.startswith(("US.", "SH.", "SZ.", "HK.")):
        return raw
    return f"US.{raw}" if raw else raw




@lru_cache(maxsize=1)
def resolve_hit_zone_root() -> Path:
    candidates = [
        os.getenv("HIT_ZONE_PROJECT_DIR"),
        str(Path.home() / "projects" / "hit-zone"),
        str(Path.home() / "projects" / "dcf-suite"),
        str(Path.home() / "codex-project"),
    ]
    for raw in candidates:
        text = str(raw or "").strip()
        if not text:
            continue
        path = Path(text).expanduser()
        if path.exists():
            return path
    return Path.home() / "projects" / "hit-zone"


@lru_cache(maxsize=1)
def _load_dcf_service() -> Any | None:
    root = resolve_hit_zone_root()
    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from dcf.repository_json import JSONRepository  # type: ignore
        from dcf.service import DCFService  # type: ignore
        return DCFService(JSONRepository(root / 'data'))
    except Exception:
        return None


@lru_cache(maxsize=256)
def diagnose_dcf_gap_batch(ticker: str, name: str = '') -> Dict[str, Any]:
    service = _load_dcf_service()
    if service is None:
        return {}
    symbol = to_dcf_symbol(ticker)
    overview: Dict[str, Any] = {}
    try:
        fetched_overview = service.get_company_overview(symbol=symbol)
        if isinstance(fetched_overview, dict):
            overview = fetched_overview
    except Exception:
        overview = {}

    try:
        profile = service._map_lookup_with_alias(service._hub_stock_profiles_index(), symbol) or {}  # noqa: SLF001
        row = {
            'name': name or profile.get('name_cn') or profile.get('name') or symbol,
            'sector': profile.get('sector'),
            'industry': profile.get('industry'),
        }
        parameter_library = service._resolve_parameter_library(  # noqa: SLF001
            symbol=symbol,
            profile=profile,
            row=row,
            allow_on_demand_metrics=True,
        )
    except Exception:
        return {}

    template_id = normalize_text(parameter_library.get('template_id'))
    family_id = normalize_text(parameter_library.get('financial_template_family_id'))
    shell_model = normalize_text(parameter_library.get('financial_template_family_shell_model'))
    valuation_mode = normalize_text(parameter_library.get('valuation_mode'))
    company_exists = isinstance(overview.get('company'), dict)
    latest_snapshot = overview.get('latest_snapshot') if isinstance(overview.get('latest_snapshot'), dict) else None
    latest_valuation = overview.get('latest_valuation') if isinstance(overview.get('latest_valuation'), dict) else None
    iv_base = optional_float((latest_valuation or {}).get('iv_base'))
    consensus_fair_value = optional_float((latest_valuation or {}).get('consensus_fair_value'))

    if template_id == 'reference_only' or normalize_text(parameter_library.get('reference_only')) in {'true', '1', 'yes'}:
        return {
            'batch_kind': 'reference_only_template_hold',
            'template_id': template_id or None,
            'family_id': family_id or None,
            'shell_model': shell_model or None,
            'reason': 'template is reference_only / non-DCF-friendly',
        }
    if latest_valuation and iv_base is not None and iv_base <= 0 and not (consensus_fair_value and consensus_fair_value > 0):
        return {
            'batch_kind': 'non_positive_dcf_hold',
            'template_id': template_id or None,
            'family_id': family_id or None,
            'shell_model': shell_model or None,
            'reason': f'latest valuation exists but iv_base<=0 ({iv_base:.4f})',
        }
    if company_exists and latest_snapshot is None:
        return {
            'batch_kind': 'snapshot_seed_batch',
            'template_id': template_id or None,
            'family_id': family_id or None,
            'shell_model': shell_model or None,
            'reason': 'company seed exists but approved financial snapshot is still missing',
        }
    if family_id and shell_model in {'ri', 'dcf'}:
        return {
            'batch_kind': 'runtime_shell_ready',
            'family_id': family_id,
            'shell_model': shell_model,
            'reason': f'financial_template_family={family_id}, shell_model={shell_model}',
        }
    if valuation_mode == 'parameterized_only':
        return {
            'batch_kind': 'structural_dcf_base',
            'family_id': family_id or None,
            'shell_model': shell_model or None,
            'reason': 'no financial shell model and valuation_mode=parameterized_only',
        }
    return {
        'batch_kind': 'dcf_focus_expansion',
        'family_id': family_id or None,
        'shell_model': shell_model or None,
        'reason': 'default dcf focus expansion',
    }


def priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(normalize_text(priority).upper(), 9)


def support_rank(support: str) -> int:
    return {
        "price_fallback": 0,
        "reference_only": 1,
        "unknown": 2,
        "formal_support": 3,
        "formal_core": 4,
    }.get(normalize_text(support), -1)



def classify_gap_item(
    gap_row: Dict[str, Any],
    *,
    real_row: Dict[str, Any] | None = None,
    signal_row: Dict[str, Any] | None = None,
    dcf_gap_batch_meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    real_row = real_row or {}
    signal_row = signal_row or {}
    ticker = normalize_text(gap_row.get("ticker"))
    signal_support = normalize_text(gap_row.get("valuation_support_tier"))
    signal_source = normalize_text(gap_row.get("valuation_source"))
    detail = normalize_text(real_row.get("valuation_source_detail"))
    current_real_source = normalize_text(real_row.get("valuation_source"))
    current_real_support = valuation_support_tier(current_real_source) if current_real_source else signal_support
    market = infer_market(ticker, signal_row.get("market") or real_row.get("market"))
    method_group = normalize_text(gap_row.get("method_group") or signal_row.get("method_group"))
    trust_bucket = normalize_text(gap_row.get("trust_bucket"))
    trust_grade = normalize_text(gap_row.get("trust_grade"))

    upgrade_lane = "formalization_review"
    target_support_tier = current_real_support if current_real_support else "reference_only"
    priority = "P2"
    issue_type = "valuation_formalization_gap"
    recommended_action = "补主估值链路或明确降级剔除规则"
    blocking_reason = detail or signal_source or "unknown"

    if support_rank(current_real_support) > support_rank(signal_support):
        upgrade_lane = "signal_refresh_reissue"
        target_support_tier = current_real_support
        issue_type = "historical_signal_source_stale"
        priority = "P0" if signal_support == "price_fallback" else "P1"
        recommended_action = (
            f"当前 real 已升级到 {current_real_source or current_real_support}；保留历史 signal 记录，但下个刷新周期按新来源重发/复核"
        )
        blocking_reason = "signal ledger 记录的是信号当时来源，不会自动回写成当前 real 来源"
    elif signal_support == "price_fallback":
        upgrade_lane = "external_valuation_prefetch"
        target_support_tier = "reference_only"
        issue_type = "external_valuation_missing"
        priority = "P0" if trust_bucket == "noisy" else "P1"
        recommended_action = "补 external_valuations 低频批量预拉；若到下个刷新周期仍缺失，则从 signal pool 暂时降级剔除"
        if "dcf_symbol_unavailable" in detail:
            blocking_reason = "缺 dcf_symbol，且 external valuation 未命中，当前只能 close_fallback"
    elif signal_support == "reference_only":
        batch_meta = dcf_gap_batch_meta if isinstance(dcf_gap_batch_meta, dict) else diagnose_dcf_gap_batch(ticker, normalize_text(gap_row.get("name")))
        batch_kind = normalize_text((batch_meta or {}).get("batch_kind"))
        target_support_tier = "formal_core" if market in {"A", "HK"} else "formal_support"
        priority = "P1"
        if batch_kind == "reference_only_template_hold":
            upgrade_lane = "formalization_review"
            issue_type = "reference_only_template_hold"
            target_support_tier = "reference_only"
            priority = "P2"
            recommended_action = "模板已明确为非 DCF 友好型，继续保留 reference_only；不再进入结构性补底座批次"
            blocking_reason = normalize_text((batch_meta or {}).get("reason")) or "template is reference_only / non-DCF-friendly"
        elif batch_kind == "non_positive_dcf_hold":
            upgrade_lane = "formalization_review"
            issue_type = "dcf_non_positive_iv"
            target_support_tier = "reference_only"
            priority = "P2"
            recommended_action = "DCF 已有结果但 iv_base<=0，当前不升级到 dcf_iv_base；继续保留 reference_only，只复核是否存在 external consensus 或规则例外"
            blocking_reason = normalize_text((batch_meta or {}).get("reason")) or "latest valuation exists but iv_base<=0"
        elif batch_kind == "snapshot_seed_batch":
            upgrade_lane = "snapshot_seed_batch"
            issue_type = "snapshot_seed_blocked"
            recommended_action = "按财报 seed / 峰值风控异常批次处理，统一重试 snapshot 入库，不逐票手工补"
            blocking_reason = normalize_text((batch_meta or {}).get("reason")) or "company exists but approved snapshot missing"
        elif batch_kind == "runtime_shell_ready":
            upgrade_lane = "dcf_runtime_shell_batch"
            issue_type = "runtime_shell_batch_ready"
            recommended_action = "按金融模板 runtime shell 批量放行，不再逐票补 symbol/seed"
            blocking_reason = normalize_text((batch_meta or {}).get("reason")) or "financial shell runtime ready"
        elif batch_kind == "structural_dcf_base":
            upgrade_lane = "structural_dcf_base_batch"
            issue_type = "structural_dcf_base_blocked"
            recommended_action = "按结构性异常批次处理：统一补 company seed / shares 入口，或统一保持 reference_only，不逐票手工补"
            blocking_reason = normalize_text((batch_meta or {}).get("reason")) or "无 financial shell model，且 valuation_mode=parameterized_only"
        elif batch_kind == "dcf_focus_expansion":
            upgrade_lane = "dcf_focus_expansion"
            issue_type = "dcf_symbol_missing"
            recommended_action = "补 dcf_symbol 映射并进入 dcf_focus_expansion 批次清单，验收后再决定是否并入 dcf_special_focus_list"
            blocking_reason = normalize_text((batch_meta or {}).get("reason")) or "当前只有 target_mean_price，且 dcf_symbol 缺失"
        else:
            upgrade_lane = "formalization_review"
            target_support_tier = "formal_support"
            issue_type = "reference_only_gap"
            priority = "P2"
            recommended_action = "确认是否能升级到 formal support；否则继续保留 reference_only"

    return {
        "priority": priority,
        "ticker": ticker,
        "name": normalize_text(gap_row.get("name") or real_row.get("name") or signal_row.get("name")),
        "market": market,
        "method_group": method_group,
        "signal_id": normalize_text(signal_row.get("signal_id")),
        "signal_as_of_date": normalize_text(signal_row.get("as_of_date")),
        "pool": normalize_text(gap_row.get("pool")),
        "signal_valuation_source": signal_source,
        "signal_support_tier": signal_support,
        "current_real_valuation_source": current_real_source,
        "current_real_support_tier": current_real_support,
        "valuation_source_detail": detail,
        "trust_bucket": trust_bucket,
        "trust_grade": trust_grade,
        "current_action": normalize_text(gap_row.get("suggested_action")),
        "upgrade_lane": upgrade_lane,
        "issue_type": issue_type,
        "blocking_reason": blocking_reason,
        "target_support_tier": target_support_tier,
        "recommended_action": recommended_action,
        "batch_kind": normalize_text((dcf_gap_batch_meta or {}).get("batch_kind")) if isinstance(dcf_gap_batch_meta, dict) else normalize_text((diagnose_dcf_gap_batch(ticker, normalize_text(gap_row.get("name"))) if signal_support == "reference_only" else {}).get("batch_kind")),
    }


def build_source_upgrade_backlog(
    *,
    coverage_doc: Dict[str, Any],
    real_rows: Sequence[Dict[str, Any]],
    signals: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    real_by_ticker = real_lookup(real_rows)
    signal_by_ticker = signal_lookup(signals)

    items = [
        classify_gap_item(
            row,
            real_row=real_by_ticker.get(normalize_text(row.get("ticker"))),
            signal_row=signal_by_ticker.get(normalize_text(row.get("ticker"))),
        )
        for row in (coverage_doc.get("gap_rows") or [])
        if isinstance(row, dict)
    ]
    items.sort(
        key=lambda row: (
            priority_rank(normalize_text(row.get("priority"))),
            normalize_text(row.get("upgrade_lane")),
            normalize_text(row.get("ticker")),
        )
    )

    by_priority: Dict[str, int] = {}
    by_lane: Dict[str, int] = {}
    target_support_breakdown: Dict[str, int] = {}
    for item in items:
        priority = normalize_text(item.get("priority")) or "P3"
        lane = normalize_text(item.get("upgrade_lane")) or "unknown"
        target = normalize_text(item.get("target_support_tier")) or "unknown"
        by_priority[priority] = by_priority.get(priority, 0) + 1
        by_lane[lane] = by_lane.get(lane, 0) + 1
        target_support_breakdown[target] = target_support_breakdown.get(target, 0) + 1

    signal_pool = coverage_doc.get("signal_pool") or {}
    signal_count = int(signal_pool.get("count") or 0)
    target_formal_count = target_support_breakdown.get("formal_core", 0) + target_support_breakdown.get("formal_support", 0)
    target_reference_count = target_support_breakdown.get("reference_only", 0)
    target_formal_rate = (target_formal_count / signal_count) if signal_count else None
    target_formal_or_reference_rate = ((target_formal_count + target_reference_count) / signal_count) if signal_count else None

    lanes: List[Dict[str, Any]] = []
    for lane in sorted(by_lane.keys()):
        lane_items = [item for item in items if normalize_text(item.get("upgrade_lane")) == lane]
        lanes.append(
            {
                "lane": lane,
                "count": len(lane_items),
                "priorities": {key: sum(1 for item in lane_items if normalize_text(item.get("priority")) == key) for key in sorted({normalize_text(item.get("priority")) for item in lane_items})},
                "target_support_tiers": {key: sum(1 for item in lane_items if normalize_text(item.get("target_support_tier")) == key) for key in sorted({normalize_text(item.get("target_support_tier")) for item in lane_items})},
                "tickers": [normalize_text(item.get("ticker")) for item in lane_items],
            }
        )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_date": normalize_text(coverage_doc.get("as_of_date")),
        "summary": {
            "gap_count": len(items),
            "priority_breakdown": by_priority,
            "lane_breakdown": by_lane,
            "current_signal_support_breakdown": dict(signal_pool.get("valuation_support_breakdown") or {}),
            "target_signal_support_breakdown_if_done": target_support_breakdown,
            "target_signal_formal_coverage_rate_if_done": target_formal_rate,
            "target_signal_formal_or_reference_coverage_rate_if_done": target_formal_or_reference_rate,
        },
        "lanes": lanes,
        "items": items,
    }


def render_source_upgrade_backlog_markdown(doc: Dict[str, Any]) -> str:
    summary = doc.get("summary") or {}
    lines: List[str] = []
    lines.append("# 估值源补强待办")
    lines.append("")
    lines.append(f"- 生成时间：{normalize_text(doc.get('generated_at_utc'))}")
    lines.append(f"- 截止日期：{normalize_text(doc.get('as_of_date')) or '-'}")
    lines.append(f"- gap 数量：{summary.get('gap_count', 0)}")
    lines.append(f"- 当前 signal 支持分布：`{summary.get('current_signal_support_breakdown') or {}}`")
    lines.append(f"- 目标 signal 支持分布（若 backlog 完成）：`{summary.get('target_signal_support_breakdown_if_done') or {}}`")
    lines.append("")
    lines.append("## 通道概览")
    lines.append("")
    lines.append("| lane | count | priorities | target tiers | tickers |")
    lines.append("|---|---:|---|---|---|")
    for row in doc.get("lanes") or []:
        lines.append(
            "| {lane} | {count} | {priorities} | {tiers} | {tickers} |".format(
                lane=normalize_text(row.get("lane")),
                count=row.get("count", 0),
                priorities=row.get("priorities") or {},
                tiers=row.get("target_support_tiers") or {},
                tickers=", ".join(row.get("tickers") or []),
            )
        )
    lines.append("")
    lines.append("## 明细")
    lines.append("")
    lines.append("| priority | 标的 | 市场 | 方法组 | signal来源 | real来源 | signal层级 | real层级 | issue | lane | 目标层级 | 建议动作 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for item in doc.get("items") or []:
        lines.append(
            "| {priority} | {name}({ticker}) | {market} | {method_group} | {signal_source} | {real_source} | {signal_support} | {real_support} | {issue} | {lane} | {target} | {action} |".format(
                priority=normalize_text(item.get("priority")),
                name=normalize_text(item.get("name")),
                ticker=normalize_text(item.get("ticker")),
                market=normalize_text(item.get("market")),
                method_group=normalize_text(item.get("method_group")) or "-",
                signal_source=normalize_text(item.get("signal_valuation_source")) or "-",
                real_source=normalize_text(item.get("current_real_valuation_source")) or "-",
                signal_support=normalize_text(item.get("signal_support_tier")) or "-",
                real_support=normalize_text(item.get("current_real_support_tier")) or "-",
                issue=normalize_text(item.get("issue_type")) or "-",
                lane=normalize_text(item.get("upgrade_lane")) or "-",
                target=normalize_text(item.get("target_support_tier")) or "-",
                action=normalize_text(item.get("recommended_action")) or "-",
            )
        )
    return "\n".join(lines) + "\n"


def load_signals(path: Path) -> List[Dict[str, Any]]:
    return load_ledger_entries(path)


# backward compatibility
def diagnose_a_hk_dcf_gap_batch(ticker: str, name: str = '') -> Dict[str, Any]:
    return diagnose_dcf_gap_batch(ticker, name)
