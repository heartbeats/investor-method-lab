from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from statistics import median
from typing import Any, Callable, Dict, Iterable, List, Sequence
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from investor_method_lab.signal_ledger import (
    dcf_symbol_to_ticker,
    normalize_internal_symbol_for_ticker,
    normalize_text,
    ticker_lookup_keys,
)

try:
    import yfinance as yf
except Exception:  # noqa: BLE001
    yf = None


HistoryLoader = Callable[[str, date, date], List[Dict[str, Any]]]

BENCHMARK_YF_SYMBOLS: Dict[str, str] = {
    "A_WIDE_CSI300": "000300.SS",
    "HK_WIDE_HSI": "^HSI",
    "US_WIDE_SPX": "^GSPC",
    "A_CONSUMPTION_CORE": "000932.SS",
    "A_TECH_GROWTH": "159915.SZ",
    "A_SEMI_AI": "512480.SS",
    "A_NEW_ENERGY_MANUFACTURING": "516160.SS",
    "A_HEALTHCARE_BIOTECH": "159992.SZ",
    "A_RESOURCE_CYCLICAL": "510410.SS",
    "A_FIN_PROPERTY": "512800.SS",
    "HK_TECH_PLATFORM": "3033.HK",
    "HK_CONSUMER_PLATFORM": "2800.HK",
    "HK_FIN_PROPERTY": "2828.HK",
    "HK_HEALTHCARE_BIOTECH": "3067.HK",
    "US_TECH_GROWTH": "XLK",
    "US_SEMI_AI": "SOXX",
    "US_CONSUMER_PLATFORM": "XLY",
    "US_CLOUD_SOFTWARE": "IGV",
    "US_HEALTHCARE_BIOTECH": "XLV",
    "US_ENERGY_INDUSTRIAL_DEFENSE": "XLI",
}

GROUP_TEMPLATE_MAP: Dict[str, str] = {
    "macro_regime": "market",
    "trend_following": "market",
    "systematic_quant": "market",
    "event_driven_activist": "event",
    "value_quality_compound": "investor_follow",
    "industry_compounder": "investor_follow",
    "garp_growth": "investor_follow",
    "deep_value_recovery": "investor_follow",
    "credit_cycle": "investor_follow",
}

DEFAULT_SNAPSHOT_ROOT = Path.home() / "projects" / "stock-data-hub" / "data_lake" / "snapshots"


def history_symbol_candidates(symbol: Any) -> List[str]:
    raw = normalize_text(symbol).upper()
    if not raw:
        return []
    candidates: List[str] = []

    def add(value: Any) -> None:
        normalized = normalize_text(value).upper()
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    if raw.startswith("^"):
        add(raw)
        add(raw.lstrip("^"))
        return candidates

    add(normalize_internal_symbol_for_ticker(raw))
    for item in ticker_lookup_keys(raw):
        add(item)
    return candidates


def _resolve_snapshot_dir(snapshot_root: Path, snapshot_date: str = "") -> Path | None:
    if not snapshot_root.exists():
        return None
    if snapshot_date:
        direct = snapshot_root / f"dt={snapshot_date}"
        if direct.exists():
            return direct
    dirs = sorted([item for item in snapshot_root.glob("dt=*") if item.is_dir()])
    if not dirs:
        return None
    return dirs[-1]


def _load_jsonl_by_symbol(path: Path) -> Dict[str, Dict[str, Any]]:
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


def _rows_from_candles(candles: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for candle in candles:
        if not isinstance(candle, dict):
            continue
        trading_date = normalize_text(candle.get("ts"))[:10]
        if not trading_date:
            continue
        rows.append(
            {
                "date": trading_date,
                "open": _safe_float(candle.get("open")),
                "high": _safe_float(candle.get("high")),
                "low": _safe_float(candle.get("low")),
                "close": _safe_float(candle.get("close")),
                "volume": _safe_float(candle.get("volume")),
            }
        )
    rows.sort(key=lambda item: normalize_text(item.get("date")))
    return rows


def _history_period_for_range(start_date: date, end_date: date) -> str:
    days = max(1, (end_date - start_date).days)
    if days <= 31:
        return "3mo"
    if days <= 93:
        return "6mo"
    if days <= 370:
        return "2y"
    return "5y"


class CompositeHistoryLoader:
    source_name = "composite_history"

    def __init__(
        self,
        *,
        snapshot_root: Path | None = None,
        snapshot_date: str = "",
        hub_url: str = "",
        allow_yfinance_fallback: bool = True,
        hub_timeout_sec: float = 6.0,
    ) -> None:
        self.snapshot_root = Path(snapshot_root) if snapshot_root else None
        self.snapshot_date = normalize_text(snapshot_date)
        self.hub_url = normalize_text(hub_url).rstrip("/")
        self.allow_yfinance_fallback = allow_yfinance_fallback
        self.hub_timeout_sec = float(hub_timeout_sec)
        self._snapshot_dir: Path | None = None
        self._snapshot_records: Dict[str, Dict[str, Any]] = {}
        self._cache: Dict[tuple[str, str, str], List[Dict[str, Any]]] = {}
        self._source_by_symbol: Dict[str, str] = {}
        if self.snapshot_root is not None:
            self._snapshot_dir = _resolve_snapshot_dir(self.snapshot_root, self.snapshot_date)
            if self._snapshot_dir is not None:
                self._snapshot_records = _load_jsonl_by_symbol(self._snapshot_dir / "price_history.jsonl")

    def describe(self) -> Dict[str, Any]:
        return {
            "snapshot_root": str(self.snapshot_root or ""),
            "snapshot_dir": str(self._snapshot_dir or ""),
            "snapshot_enabled": bool(self._snapshot_records),
            "hub_url": self.hub_url,
            "yfinance_fallback": self.allow_yfinance_fallback,
        }

    def source_for_symbol(self, symbol: Any) -> str:
        key = normalize_text(symbol).upper()
        return self._source_by_symbol.get(key, f"history_loader:{normalize_text(symbol)}")

    def __call__(self, symbol: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        key = (normalize_text(symbol).upper(), start_date.isoformat(), end_date.isoformat())
        if key in self._cache:
            return list(self._cache[key])
        rows, source, errors = self._load_rows(symbol, start_date, end_date)
        self._source_by_symbol[key[0]] = source
        if not rows:
            message = "; ".join(errors) or f"history_unavailable:{symbol}"
            raise RuntimeError(message[:240])
        self._cache[key] = rows
        return list(rows)

    def _load_rows(self, symbol: str, start_date: date, end_date: date) -> tuple[List[Dict[str, Any]], str, List[str]]:
        errors: List[str] = []
        start_key = start_date.isoformat()
        end_key = end_date.isoformat()
        for candidate in history_symbol_candidates(symbol):
            payload = self._snapshot_records.get(candidate)
            if not isinstance(payload, dict):
                continue
            rows = [
                row
                for row in _rows_from_candles(payload.get("candles") or [])
                if start_key <= normalize_text(row.get("date")) <= end_key
            ]
            if rows:
                return rows, f"snapshot:{candidate}", errors

        if self.hub_url and not normalize_text(symbol).startswith("^"):
            period = _history_period_for_range(start_date, end_date)
            for candidate in history_symbol_candidates(symbol):
                try:
                    payload = self._fetch_hub_history(candidate, period)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"hub:{candidate}:{str(exc)[:80]}")
                    continue
                rows = [
                    row
                    for row in _rows_from_candles(payload.get("candles") or [])
                    if start_key <= normalize_text(row.get("date")) <= end_key
                ]
                if rows:
                    return rows, f"stock_data_hub:{candidate}", errors

        if self.allow_yfinance_fallback:
            try:
                rows = default_history_loader(symbol, start_date, end_date)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"yfinance:{symbol}:{str(exc)[:80]}")
            else:
                if rows:
                    return rows, f"yfinance:{symbol}", errors
                errors.append(f"yfinance:{symbol}:empty")

        return [], f"history_unavailable:{symbol}", errors

    def _fetch_hub_history(self, symbol: str, period: str) -> Dict[str, Any]:
        query = urllib_parse.urlencode(
            {
                "symbol": symbol,
                "period": period,
                "interval": "1d",
                "mode": "non_realtime",
                "refresh": "false",
            }
        )
        url = f"{self.hub_url}/v1/price-history?{query}"
        opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
        req = urllib_request.Request(url, headers={"Accept": "application/json"})
        with opener.open(req, timeout=max(1.0, self.hub_timeout_sec)) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError(f"invalid hub payload:{symbol}")
        return payload


def build_history_loader(
    *,
    snapshot_root: Path | None = DEFAULT_SNAPSHOT_ROOT,
    snapshot_date: str = "",
    hub_url: str = "",
    allow_yfinance_fallback: bool = True,
    hub_timeout_sec: float = 6.0,
) -> CompositeHistoryLoader:
    return CompositeHistoryLoader(
        snapshot_root=snapshot_root,
        snapshot_date=snapshot_date,
        hub_url=hub_url,
        allow_yfinance_fallback=allow_yfinance_fallback,
        hub_timeout_sec=hub_timeout_sec,
    )



@dataclass
class PositionEvaluation:
    signal_id: str
    ticker: str
    name: str
    market: str
    method_group: str
    method_group_id: str
    template_id: str
    valuation_source_at_signal: str
    valuation_support_tier: str
    signal_date: str
    validation_as_of_date: str
    status: str
    entry_date: str
    entry_price: float | None
    entry_price_source: str
    exit_date: str
    exit_price: float | None
    exit_reason: str
    days_held: int
    strategy_return_gross: float | None
    strategy_return_net: float | None
    primary_benchmark_return: float | None
    primary_excess_return: float | None
    secondary_benchmark_return: float | None
    secondary_excess_return: float | None
    max_drawdown: float | None
    hit: bool | None
    valuation_realized: bool | None
    price_history_source: str
    benchmark_primary_id: str
    benchmark_secondary_id: str
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "ticker": self.ticker,
            "name": self.name,
            "market": self.market,
            "method_group": self.method_group,
            "method_group_id": self.method_group_id,
            "template_id": self.template_id,
            "valuation_source_at_signal": self.valuation_source_at_signal,
            "valuation_support_tier": self.valuation_support_tier,
            "signal_date": self.signal_date,
            "validation_as_of_date": self.validation_as_of_date,
            "status": self.status,
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "entry_price_source": self.entry_price_source,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "days_held": self.days_held,
            "strategy_return_gross": self.strategy_return_gross,
            "strategy_return_net": self.strategy_return_net,
            "primary_benchmark_return": self.primary_benchmark_return,
            "primary_excess_return": self.primary_excess_return,
            "secondary_benchmark_return": self.secondary_benchmark_return,
            "secondary_excess_return": self.secondary_excess_return,
            "max_drawdown": self.max_drawdown,
            "hit": self.hit,
            "valuation_realized": self.valuation_realized,
            "price_history_source": self.price_history_source,
            "benchmark_primary_id": self.benchmark_primary_id,
            "benchmark_secondary_id": self.benchmark_secondary_id,
            "notes": self.notes,
        }



def parse_iso_date(value: Any) -> date:
    text = normalize_text(value)
    return datetime.strptime(text[:10], "%Y-%m-%d").date()



def resolve_template_id(signal: Dict[str, Any], validation_rules: Dict[str, Any]) -> str:
    method_templates = (validation_rules.get("method_templates") or {})
    valuation_source = normalize_text(signal.get("valuation_source_at_signal"))
    method_group_id = normalize_text(signal.get("method_group_id"))
    if valuation_source == "dcf_iv_base" and "dcf" in method_templates:
        return "dcf"
    return GROUP_TEMPLATE_MAP.get(method_group_id, "investor_follow")



def valuation_support_tier(valuation_source: Any) -> str:
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



def to_yfinance_symbol(signal: Dict[str, Any]) -> str:
    symbol = normalize_text(signal.get("symbol"))
    ticker = normalize_text(signal.get("ticker"))
    if symbol.startswith(("SH.", "SZ.", "HK.", "US.")):
        return dcf_symbol_to_ticker(symbol)
    return ticker



def default_history_loader(yf_symbol: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    if yf is None:
        raise RuntimeError("yfinance not available")
    ticker = yf.Ticker(yf_symbol)
    history = ticker.history(
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=False,
        actions=False,
    )
    rows: List[Dict[str, Any]] = []
    if history is None or getattr(history, "empty", True):
        return rows
    for idx, row in history.iterrows():
        dt = getattr(idx, "to_pydatetime", lambda: idx)()
        trading_date = dt.date().isoformat()
        rows.append(
            {
                "date": trading_date,
                "open": _safe_float(row.get("Open")),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": _safe_float(row.get("Close")),
            }
        )
    return rows


default_history_loader.source_name = "yfinance"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return None



def select_entry_bar(price_rows: Sequence[Dict[str, Any]], signal_date: date) -> tuple[Dict[str, Any] | None, str, List[str]]:
    notes: List[str] = []
    for row in price_rows:
        row_date = parse_iso_date(row.get("date"))
        if row_date <= signal_date:
            continue
        open_price = _safe_float(row.get("open"))
        close_price = _safe_float(row.get("close"))
        if open_price is not None and open_price > 0:
            return row, "next_trading_day_open", notes
        if close_price is not None and close_price > 0:
            notes.append("entry_fallback_to_close")
            return row, "next_trading_day_close_with_flag", notes
    notes.append("pending_next_trading_day")
    return None, "pending", notes



def _net_return(entry_price: float, exit_price: float, buy_cost: float, sell_cost: float) -> float:
    effective_entry = entry_price * (1.0 + buy_cost)
    effective_exit = exit_price * (1.0 - sell_cost)
    return (effective_exit / effective_entry) - 1.0



def _open_position_net_return(entry_price: float, current_price: float, buy_cost: float) -> float:
    effective_entry = entry_price * (1.0 + buy_cost)
    return (current_price / effective_entry) - 1.0



def _calculate_max_drawdown(price_rows: Sequence[Dict[str, Any]], start_index: int) -> float | None:
    closes = [
        _safe_float(row.get("close"))
        for row in price_rows[start_index:]
        if _safe_float(row.get("close")) is not None
    ]
    if not closes:
        return None
    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        if close > peak:
            peak = close
        drawdown = (close / peak) - 1.0
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    return max_drawdown



def _resolve_secondary_history(
    signal: Dict[str, Any],
    start_date: date,
    end_date: date,
    history_loader: HistoryLoader,
) -> tuple[str, List[Dict[str, Any]], List[str]]:
    secondary = signal.get("secondary_benchmark") or {}
    benchmark_id = normalize_text(secondary.get("benchmark_id"))
    if not benchmark_id:
        return "", [], ["secondary_benchmark_missing"]
    yf_symbol = BENCHMARK_YF_SYMBOLS.get(benchmark_id, "")
    if not yf_symbol:
        return benchmark_id, [], [f"secondary_benchmark_unmapped:{benchmark_id}"]
    try:
        return benchmark_id, history_loader(yf_symbol, start_date, end_date), []
    except Exception as exc:  # noqa: BLE001
        return benchmark_id, [], [f"secondary_benchmark_fetch_failed:{benchmark_id}:{str(exc)[:120]}"]



def _resolve_primary_history(
    signal: Dict[str, Any],
    start_date: date,
    end_date: date,
    history_loader: HistoryLoader,
) -> tuple[str, List[Dict[str, Any]], List[str]]:
    primary = signal.get("primary_benchmark") or {}
    benchmark_id = normalize_text(primary.get("benchmark_id"))
    if not benchmark_id:
        return "", [], ["primary_benchmark_missing"]
    yf_symbol = BENCHMARK_YF_SYMBOLS.get(benchmark_id, "")
    if not yf_symbol:
        return benchmark_id, [], [f"primary_benchmark_unmapped:{benchmark_id}"]
    try:
        return benchmark_id, history_loader(yf_symbol, start_date, end_date), []
    except Exception as exc:  # noqa: BLE001
        return benchmark_id, [], [f"primary_benchmark_fetch_failed:{benchmark_id}:{str(exc)[:120]}"]



def _lookup_close_on_or_before(rows: Sequence[Dict[str, Any]], target_date: str) -> float | None:
    value: float | None = None
    for row in rows:
        row_date = normalize_text(row.get("date"))
        if row_date > target_date:
            break
        close = _safe_float(row.get("close"))
        if close is not None:
            value = close
    return value


def _history_source_for_symbol(history_loader: HistoryLoader, symbol: str) -> str:
    resolver = getattr(history_loader, "source_for_symbol", None)
    if callable(resolver):
        source = normalize_text(resolver(symbol))
        if source:
            return source
    source_name = normalize_text(getattr(history_loader, "source_name", ""))
    if source_name:
        return f"{source_name}:{symbol}"
    fallback_name = normalize_text(getattr(history_loader, "__name__", "history_loader"))
    return f"{fallback_name}:{symbol}"


def evaluate_signal(
    signal: Dict[str, Any],
    validation_rules: Dict[str, Any],
    validation_as_of_date: date,
    history_loader: HistoryLoader = default_history_loader,
) -> PositionEvaluation:
    method_templates = validation_rules.get("method_templates") or {}
    friction_costs = validation_rules.get("friction_costs") or {}
    template_id = resolve_template_id(signal, validation_rules)
    template = method_templates.get(template_id) or method_templates.get("investor_follow") or {}
    market = normalize_text(signal.get("market")) or "US"
    valuation_source = normalize_text(signal.get("valuation_source_at_signal"))
    valuation_support = valuation_support_tier(valuation_source)
    signal_date = parse_iso_date(signal.get("as_of_date"))
    yf_symbol = to_yfinance_symbol(signal)
    start_date = signal_date - timedelta(days=7)
    end_date = validation_as_of_date
    notes: List[str] = []

    try:
        price_rows = history_loader(yf_symbol, start_date, end_date)
        price_history_source = _history_source_for_symbol(history_loader, yf_symbol)
    except Exception as exc:  # noqa: BLE001
        price_rows = []
        price_history_source = f"history_fetch_failed:{yf_symbol}"
        notes.append(str(exc)[:160])

    entry_row, entry_source, entry_notes = select_entry_bar(price_rows, signal_date)
    notes.extend(entry_notes)
    primary_benchmark_id = normalize_text((signal.get("primary_benchmark") or {}).get("benchmark_id"))
    secondary_benchmark_id = normalize_text((signal.get("secondary_benchmark") or {}).get("benchmark_id"))

    if entry_row is None:
        return PositionEvaluation(
            signal_id=normalize_text(signal.get("signal_id")),
            ticker=normalize_text(signal.get("ticker")),
            name=normalize_text(signal.get("name")),
            market=market,
            method_group=normalize_text(signal.get("method_group")),
            method_group_id=normalize_text(signal.get("method_group_id")),
            template_id=template_id,
            valuation_source_at_signal=valuation_source,
            valuation_support_tier=valuation_support,
            signal_date=signal_date.isoformat(),
            validation_as_of_date=validation_as_of_date.isoformat(),
            status="pending_entry",
            entry_date="",
            entry_price=None,
            entry_price_source=entry_source,
            exit_date="",
            exit_price=None,
            exit_reason="pending_next_trading_day",
            days_held=0,
            strategy_return_gross=None,
            strategy_return_net=None,
            primary_benchmark_return=None,
            primary_excess_return=None,
            secondary_benchmark_return=None,
            secondary_excess_return=None,
            max_drawdown=None,
            hit=None,
            valuation_realized=None,
            price_history_source=price_history_source,
            benchmark_primary_id=primary_benchmark_id,
            benchmark_secondary_id=secondary_benchmark_id,
            notes=notes,
        )

    entry_date = normalize_text(entry_row.get("date"))
    entry_price = _safe_float(entry_row.get("open")) if entry_source == "next_trading_day_open" else _safe_float(entry_row.get("close"))
    if entry_price is None:
        notes.append("entry_price_missing")
        return PositionEvaluation(
            signal_id=normalize_text(signal.get("signal_id")),
            ticker=normalize_text(signal.get("ticker")),
            name=normalize_text(signal.get("name")),
            market=market,
            method_group=normalize_text(signal.get("method_group")),
            method_group_id=normalize_text(signal.get("method_group_id")),
            template_id=template_id,
            valuation_source_at_signal=valuation_source,
            valuation_support_tier=valuation_support,
            signal_date=signal_date.isoformat(),
            validation_as_of_date=validation_as_of_date.isoformat(),
            status="pending_entry",
            entry_date=entry_date,
            entry_price=None,
            entry_price_source=entry_source,
            exit_date="",
            exit_price=None,
            exit_reason="entry_price_missing",
            days_held=0,
            strategy_return_gross=None,
            strategy_return_net=None,
            primary_benchmark_return=None,
            primary_excess_return=None,
            secondary_benchmark_return=None,
            secondary_excess_return=None,
            max_drawdown=None,
            hit=None,
            valuation_realized=None,
            price_history_source=price_history_source,
            benchmark_primary_id=primary_benchmark_id,
            benchmark_secondary_id=secondary_benchmark_id,
            notes=notes,
        )

    primary_benchmark_id, primary_rows, primary_notes = _resolve_primary_history(signal, start_date, end_date, history_loader)
    notes.extend(primary_notes)
    secondary_benchmark_id, secondary_rows, secondary_notes = _resolve_secondary_history(signal, start_date, end_date, history_loader)
    notes.extend(secondary_notes)

    buy_cost = float((friction_costs.get(market) or {}).get("buy_total_cost") or 0.0)
    sell_cost = float((friction_costs.get(market) or {}).get("sell_total_cost") or 0.0)
    exit_priority = template.get("exit_priority") or []
    target_return = _rule_threshold(exit_priority, prefix="return_gte_")
    stop_return = _rule_threshold(exit_priority, prefix="drawdown_lte_")
    max_holding_days = _rule_holding_days(exit_priority)
    fair_value = _safe_float(signal.get("fair_value_at_signal"))

    entry_index = next((idx for idx, row in enumerate(price_rows) if normalize_text(row.get("date")) == entry_date), None)
    if entry_index is None:
        entry_index = 0

    exit_date = ""
    exit_price: float | None = None
    exit_reason = ""
    status = "open"
    valuation_realized = False
    days_held = 0

    for offset, row in enumerate(price_rows[entry_index:], start=1):
        current_date = normalize_text(row.get("date"))
        high_price = _safe_float(row.get("high")) or _safe_float(row.get("close"))
        low_price = _safe_float(row.get("low")) or _safe_float(row.get("close"))
        close_price = _safe_float(row.get("close"))
        if close_price is None:
            continue
        days_held = offset
        if template_id == "dcf" and fair_value is not None and high_price is not None:
            if high_price >= fair_value:
                exit_date = current_date
                exit_price = close_price
                exit_reason = "price_reaches_signal_fv50"
                status = "closed"
                valuation_realized = True
                break
        if target_return is not None and high_price is not None and ((high_price / entry_price) - 1.0) >= target_return:
            exit_date = current_date
            exit_price = close_price
            exit_reason = f"return_gte_{int(target_return * 100)}pct"
            status = "closed"
            if fair_value is not None and high_price >= fair_value:
                valuation_realized = True
            break
        if stop_return is not None and low_price is not None and ((low_price / entry_price) - 1.0) <= stop_return:
            exit_date = current_date
            exit_price = close_price
            exit_reason = f"drawdown_lte_{int(stop_return * 100)}pct"
            status = "closed"
            break
        if template_id == "dcf" and fair_value is not None:
            mos = 1.0 - (close_price / fair_value)
            if mos <= 0.10:
                exit_date = current_date
                exit_price = close_price
                exit_reason = "mos_fv_compresses_to_lte_10pct"
                status = "closed"
                valuation_realized = True
                break
        if max_holding_days is not None and offset >= max_holding_days:
            exit_date = current_date
            exit_price = close_price
            exit_reason = f"holding_days_gte_{max_holding_days}"
            status = "expired"
            break

    if not exit_date:
        last_close = None
        last_date = ""
        for row in reversed(price_rows):
            if _safe_float(row.get("close")) is not None:
                last_close = _safe_float(row.get("close"))
                last_date = normalize_text(row.get("date"))
                break
        exit_date = last_date
        exit_price = last_close
        exit_reason = "mark_to_market"
        status = "open"
        if template_id == "dcf" and fair_value is not None and exit_price is not None:
            valuation_realized = exit_price >= fair_value or (1.0 - (exit_price / fair_value)) <= 0.10
        elif template_id != "dcf":
            valuation_realized = None

    strategy_return_gross = None
    strategy_return_net = None
    if exit_price is not None:
        strategy_return_gross = (exit_price / entry_price) - 1.0
        if status == "open":
            strategy_return_net = _open_position_net_return(entry_price, exit_price, buy_cost)
        else:
            strategy_return_net = _net_return(entry_price, exit_price, buy_cost, sell_cost)

    primary_benchmark_return = None
    if entry_date:
        primary_entry = _lookup_close_on_or_before(primary_rows, entry_date)
        primary_exit = _lookup_close_on_or_before(primary_rows, exit_date)
        if primary_entry is not None and primary_exit is not None and primary_entry > 0:
            primary_benchmark_return = (primary_exit / primary_entry) - 1.0

    secondary_benchmark_return = None
    if entry_date and secondary_rows:
        secondary_entry = _lookup_close_on_or_before(secondary_rows, entry_date)
        secondary_exit = _lookup_close_on_or_before(secondary_rows, exit_date)
        if secondary_entry is not None and secondary_exit is not None and secondary_entry > 0:
            secondary_benchmark_return = (secondary_exit / secondary_entry) - 1.0

    primary_excess_return = (
        strategy_return_net - primary_benchmark_return
        if strategy_return_net is not None and primary_benchmark_return is not None
        else None
    )
    secondary_excess_return = (
        strategy_return_net - secondary_benchmark_return
        if strategy_return_net is not None and secondary_benchmark_return is not None
        else None
    )
    hit = None
    if strategy_return_net is not None:
        hit = strategy_return_net > 0 or (primary_excess_return is not None and primary_excess_return > 0)

    max_drawdown = _calculate_max_drawdown(price_rows, entry_index)

    return PositionEvaluation(
        signal_id=normalize_text(signal.get("signal_id")),
        ticker=normalize_text(signal.get("ticker")),
        name=normalize_text(signal.get("name")),
        market=market,
        method_group=normalize_text(signal.get("method_group")),
        method_group_id=normalize_text(signal.get("method_group_id")),
        template_id=template_id,
        valuation_source_at_signal=valuation_source,
        valuation_support_tier=valuation_support,
        signal_date=signal_date.isoformat(),
        validation_as_of_date=validation_as_of_date.isoformat(),
        status=status,
        entry_date=entry_date,
        entry_price=entry_price,
        entry_price_source=entry_source,
        exit_date=exit_date,
        exit_price=exit_price,
        exit_reason=exit_reason,
        days_held=days_held,
        strategy_return_gross=strategy_return_gross,
        strategy_return_net=strategy_return_net,
        primary_benchmark_return=primary_benchmark_return,
        primary_excess_return=primary_excess_return,
        secondary_benchmark_return=secondary_benchmark_return,
        secondary_excess_return=secondary_excess_return,
        max_drawdown=max_drawdown,
        hit=hit,
        valuation_realized=valuation_realized,
        price_history_source=price_history_source,
        benchmark_primary_id=primary_benchmark_id,
        benchmark_secondary_id=secondary_benchmark_id,
        notes=notes,
    )



def _rule_threshold(exit_priority: Sequence[str], prefix: str) -> float | None:
    for item in exit_priority:
        text = normalize_text(item)
        if text.startswith(prefix) and text.endswith("pct"):
            raw = text[len(prefix):-3]
            try:
                return float(raw) / 100.0
            except ValueError:
                return None
    return None



def _rule_holding_days(exit_priority: Sequence[str]) -> int | None:
    for item in exit_priority:
        text = normalize_text(item)
        if text.startswith("holding_days_gte_"):
            raw = text[len("holding_days_gte_"):]
            try:
                return int(raw)
            except ValueError:
                return None
    return None



def evaluate_signals(
    signals: Iterable[Dict[str, Any]],
    validation_rules: Dict[str, Any],
    validation_as_of_date: date,
    history_loader: HistoryLoader = default_history_loader,
) -> List[Dict[str, Any]]:
    rows = [
        evaluate_signal(
            signal=signal,
            validation_rules=validation_rules,
            validation_as_of_date=validation_as_of_date,
            history_loader=history_loader,
        ).to_dict()
        for signal in signals
    ]
    rows.sort(
        key=lambda item: (
            normalize_text(item.get("status")),
            -(item.get("primary_excess_return") or -999),
            -(item.get("strategy_return_net") or -999),
        )
    )
    return rows



def summarize_validation(
    positions: List[Dict[str, Any]],
    validation_rules: Dict[str, Any],
    validation_as_of_date: date,
    ledger_file: Path,
) -> Dict[str, Any]:
    status_breakdown = _count_by(positions, "status")
    template_breakdown = _count_by(positions, "template_id")
    valuation_source_breakdown = _count_by(positions, "valuation_source_at_signal")
    valuation_support_breakdown = _count_by(positions, "valuation_support_tier")
    valuation_support_summary = {
        support: _summarize_position_slice(
            [row for row in positions if normalize_text(row.get("valuation_support_tier")) == support]
        )
        for support in sorted({normalize_text(row.get("valuation_support_tier")) for row in positions if normalize_text(row.get("valuation_support_tier"))})
    }
    method_group_summary: Dict[str, Dict[str, Any]] = {}
    for position in positions:
        group = normalize_text(position.get("method_group")) or "<empty>"
        bucket = method_group_summary.setdefault(
            group,
            {
                "count": 0,
                "entered_count": 0,
                "open_count": 0,
                "closed_count": 0,
                "expired_count": 0,
                "pending_entry_count": 0,
                "avg_strategy_return_net": None,
                "avg_primary_excess_return": None,
                "hit_rate": None,
                "win_rate": None,
                "profit_loss_ratio": None,
                "valuation_realization_rate": None,
                "median_days_held": None,
                "max_drawdown_worst": None,
            },
        )
        bucket["count"] += 1
        status = normalize_text(position.get("status"))
        bucket[f"{status}_count"] = bucket.get(f"{status}_count", 0) + 1
        if status != "pending_entry":
            bucket["entered_count"] += 1

    for group, bucket in method_group_summary.items():
        rows = [row for row in positions if normalize_text(row.get("method_group")) == group and normalize_text(row.get("status")) != "pending_entry"]
        returns = [row.get("strategy_return_net") for row in rows if row.get("strategy_return_net") is not None]
        excess = [row.get("primary_excess_return") for row in rows if row.get("primary_excess_return") is not None]
        hits = [bool(row.get("hit")) for row in rows if row.get("hit") is not None]
        wins = [value for value in returns if value is not None and value > 0]
        losses = [value for value in returns if value is not None and value < 0]
        realizations = [bool(row.get("valuation_realized")) for row in rows if row.get("valuation_realized") is not None]
        holding_days = [int(row.get("days_held") or 0) for row in rows if row.get("days_held") is not None]
        drawdowns = [row.get("max_drawdown") for row in rows if row.get("max_drawdown") is not None]
        bucket["avg_strategy_return_net"] = _average(returns)
        bucket["avg_primary_excess_return"] = _average(excess)
        bucket["hit_rate"] = (_average([1.0 if item else 0.0 for item in hits]) if hits else None)
        bucket["win_rate"] = (_average([1.0 if item > 0 else 0.0 for item in returns]) if returns else None)
        bucket["profit_loss_ratio"] = (
            (_average(wins) / abs(_average(losses)))
            if wins and losses and _average(losses) not in {None, 0}
            else None
        )
        bucket["valuation_realization_rate"] = (
            _average([1.0 if item else 0.0 for item in realizations]) if realizations else None
        )
        bucket["median_days_held"] = (median(holding_days) if holding_days else None)
        bucket["max_drawdown_worst"] = (min(drawdowns) if drawdowns else None)

    evaluated_positions = [row for row in positions if normalize_text(row.get("status")) != "pending_entry"]
    overall_returns = [row.get("strategy_return_net") for row in evaluated_positions if row.get("strategy_return_net") is not None]
    overall_excess = [row.get("primary_excess_return") for row in evaluated_positions if row.get("primary_excess_return") is not None]
    overall_hits = [bool(row.get("hit")) for row in evaluated_positions if row.get("hit") is not None]
    overall_drawdowns = [row.get("max_drawdown") for row in evaluated_positions if row.get("max_drawdown") is not None]
    overall_realizations = [bool(row.get("valuation_realized")) for row in evaluated_positions if row.get("valuation_realized") is not None]

    minimums = validation_rules.get("minimum_viable_thresholds") or {}
    overall_summary = {
        "evaluated_signal_count": len(evaluated_positions),
        "avg_strategy_return_net": _average(overall_returns),
        "avg_primary_excess_return": _average(overall_excess),
        "opportunity_hit_rate": (_average([1.0 if item else 0.0 for item in overall_hits]) if overall_hits else None),
        "profit_loss_ratio": _profit_loss_ratio(overall_returns),
        "max_drawdown": (min(overall_drawdowns) if overall_drawdowns else None),
        "valuation_realization_rate": (_average([1.0 if item else 0.0 for item in overall_realizations]) if overall_realizations else None),
        "minimum_viable_threshold_checks": {
            metric: _evaluate_threshold(
                {
                    "opportunity_excess_return": _average(overall_excess),
                    "opportunity_hit_rate": (_average([1.0 if item else 0.0 for item in overall_hits]) if overall_hits else None),
                    "profit_loss_ratio": _profit_loss_ratio(overall_returns),
                    "max_drawdown": (min(overall_drawdowns) if overall_drawdowns else None),
                    "valuation_realization_rate": (_average([1.0 if item else 0.0 for item in overall_realizations]) if overall_realizations else None),
                }.get(metric),
                rule,
            )
            for metric, rule in minimums.items()
        },
    }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_as_of_date": validation_as_of_date.isoformat(),
        "ledger_file": str(ledger_file),
        "total_signals": len(positions),
        "status_breakdown": status_breakdown,
        "template_breakdown": template_breakdown,
        "valuation_source_breakdown": valuation_source_breakdown,
        "valuation_support_breakdown": valuation_support_breakdown,
        "valuation_support_summary": valuation_support_summary,
        "overall_summary": overall_summary,
        "method_group_summary": method_group_summary,
        "top_winners": _top_positions(positions, key="primary_excess_return", reverse=True),
        "top_losers": _top_positions(positions, key="primary_excess_return", reverse=False),
        "positions_file": "",
    }



def _summarize_position_slice(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    evaluated = [row for row in rows if normalize_text(row.get("status")) != "pending_entry"]
    returns = [row.get("strategy_return_net") for row in evaluated if row.get("strategy_return_net") is not None]
    excess = [row.get("primary_excess_return") for row in evaluated if row.get("primary_excess_return") is not None]
    hits = [bool(row.get("hit")) for row in evaluated if row.get("hit") is not None]
    return {
        "count": len(rows),
        "evaluated_count": len(evaluated),
        "open_count": sum(1 for row in rows if normalize_text(row.get("status")) == "open"),
        "closed_count": sum(1 for row in rows if normalize_text(row.get("status")) == "closed"),
        "expired_count": sum(1 for row in rows if normalize_text(row.get("status")) == "expired"),
        "pending_entry_count": sum(1 for row in rows if normalize_text(row.get("status")) == "pending_entry"),
        "avg_strategy_return_net": _average(returns),
        "avg_primary_excess_return": _average(excess),
        "hit_rate": (_average([1.0 if item else 0.0 for item in hits]) if hits else None),
    }



def render_validation_markdown(summary: Dict[str, Any], positions: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# 机会验真最新报表")
    lines.append("")
    lines.append(f"- 生成时间：{normalize_text(summary.get('generated_at_utc'))}")
    lines.append(f"- 验真截止日：{normalize_text(summary.get('validation_as_of_date'))}")
    lines.append(f"- 账本文件：`{normalize_text(summary.get('ledger_file'))}`")
    lines.append(f"- 总信号数：{summary.get('total_signals', 0)}")
    loader_context = summary.get('history_loader_context') or {}
    if loader_context:
        lines.append(
            f"- 行情加载：snapshot=`{normalize_text(loader_context.get('snapshot_dir')) or '-'}` | hub=`{normalize_text(loader_context.get('hub_url')) or '-'}` | yfinance兜底=`{'on' if loader_context.get('yfinance_fallback') else 'off'}`"
        )
    lines.append("")
    lines.append("## 状态分布")
    lines.append("")
    lines.append(f"- 状态：`{json.dumps(summary.get('status_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 模板：`{json.dumps(summary.get('template_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 估值来源：`{json.dumps(summary.get('valuation_source_breakdown') or {}, ensure_ascii=False)}`")
    lines.append(f"- 估值支持：`{json.dumps(summary.get('valuation_support_breakdown') or {}, ensure_ascii=False)}`")
    lines.append("")

    overall = summary.get("overall_summary") or {}
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 已进入评估的信号数：{overall.get('evaluated_signal_count', 0)}")
    lines.append(f"- 平均策略净收益：{_fmt_pct(overall.get('avg_strategy_return_net'))}")
    lines.append(f"- 平均一级基准超额：{_fmt_pct(overall.get('avg_primary_excess_return'))}")
    lines.append(f"- 机会命中率：{_fmt_pct(overall.get('opportunity_hit_rate'))}")
    lines.append(f"- 盈亏比：{_fmt_num(overall.get('profit_loss_ratio'))}")
    lines.append(f"- 最大回撤：{_fmt_pct(overall.get('max_drawdown'))}")
    lines.append(f"- 估值兑现率：{_fmt_pct(overall.get('valuation_realization_rate'))}")
    lines.append("")

    lines.append("## 估值支持分层")
    lines.append("")
    lines.append("| 支持层级 | 样本 | 已评估 | Open | Closed | Expired | Pending | 平均净收益 | 一级超额 | 命中率 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for support, row in sorted((summary.get("valuation_support_summary") or {}).items()):
        lines.append(
            "| {support} | {count} | {evaluated} | {open_count} | {closed_count} | {expired_count} | {pending_count} | {avg_return} | {avg_excess} | {hit_rate} |".format(
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
            )
        )
    lines.append("")

    lines.append("## 方法组汇总")
    lines.append("")
    lines.append("| 方法组 | 样本 | 已评估 | Pending | Open | Closed | Expired | 平均净收益 | 一级超额 | 命中率 | 盈亏比 | 兑现率 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for group, bucket in sorted((summary.get("method_group_summary") or {}).items()):
        lines.append(
            "| {group} | {count} | {entered} | {pending_count} | {open_count} | {closed_count} | {expired_count} | {avg_return} | {avg_excess} | {hit_rate} | {pl_ratio} | {realization} |".format(
                group=group,
                count=bucket.get("count", 0),
                entered=bucket.get("entered_count", 0),
                pending_count=bucket.get("pending_entry_count", 0),
                open_count=bucket.get("open_count", 0),
                closed_count=bucket.get("closed_count", 0),
                expired_count=bucket.get("expired_count", 0),
                avg_return=_fmt_pct(bucket.get("avg_strategy_return_net")),
                avg_excess=_fmt_pct(bucket.get("avg_primary_excess_return")),
                hit_rate=_fmt_pct(bucket.get("hit_rate")),
                pl_ratio=_fmt_num(bucket.get("profit_loss_ratio")),
                realization=_fmt_pct(bucket.get("valuation_realization_rate")),
            )
        )
    lines.append("")

    lines.append("## 最新持仓明细")
    lines.append("")
    lines.append("| 标的 | 状态 | 模板 | 入场日 | 退出/估值日 | 净收益 | 一级超额 | 持有天数 | 原因 |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---|")
    for row in positions[:20]:
        lines.append(
            "| {name}({ticker}) | {status} | {template} | {entry_date} | {exit_date} | {net_return} | {excess} | {days_held} | {reason} |".format(
                name=normalize_text(row.get("name")),
                ticker=normalize_text(row.get("ticker")),
                status=normalize_text(row.get("status")),
                template=normalize_text(row.get("template_id")),
                entry_date=normalize_text(row.get("entry_date")) or "-",
                exit_date=normalize_text(row.get("exit_date")) or "-",
                net_return=_fmt_pct(row.get("strategy_return_net")),
                excess=_fmt_pct(row.get("primary_excess_return")),
                days_held=int(row.get("days_held") or 0),
                reason=normalize_text(row.get("exit_reason")).replace("|", "/") or "-",
            )
        )
    return "\n".join(lines) + "\n"



def load_validation_rules(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))



def _average(values: Sequence[float | None]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)



def _profit_loss_ratio(values: Sequence[float | None]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    wins = [value for value in filtered if value > 0]
    losses = [value for value in filtered if value < 0]
    if not wins or not losses:
        return None
    avg_loss = _average(losses)
    if avg_loss in {None, 0}:
        return None
    return _average(wins) / abs(avg_loss)



def _count_by(rows: Iterable[Dict[str, Any]], field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        key = normalize_text(row.get(field)) or "<empty>"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))



def _evaluate_threshold(value: float | None, rule: Dict[str, Any]) -> Dict[str, Any]:
    op = normalize_text(rule.get("op"))
    target = _safe_float(rule.get("value"))
    passed = None
    if value is not None and target is not None:
        if op == "gt":
            passed = value > target
        elif op == "gte":
            passed = value >= target
        elif op == "lte":
            passed = value <= target
    return {"value": value, "target": target, "op": op, "passed": passed}



def _top_positions(positions: List[Dict[str, Any]], key: str, reverse: bool) -> List[Dict[str, Any]]:
    filtered = [row for row in positions if row.get(key) is not None]
    filtered.sort(key=lambda row: float(row.get(key) or 0.0), reverse=reverse)
    return [
        {
            "ticker": row.get("ticker"),
            "name": row.get("name"),
            key: row.get(key),
            "status": row.get("status"),
            "template_id": row.get("template_id"),
        }
        for row in filtered[:10]
    ]



def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.2f}%"



def _fmt_num(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"
