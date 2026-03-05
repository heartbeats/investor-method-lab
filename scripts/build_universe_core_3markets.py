#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]

US_SP500_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
)
HKEX_SECURITIES_URL = (
    "https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx"
)
SSE_STOCK_LIST_URL = (
    "http://query.sse.com.cn/security/stock/getStockListData2.do"
    "?isPagination=true&stockType=1&pageHelp.pageSize=5000&pageHelp.pageNo=1"
    "&pageHelp.beginPage=1&pageHelp.endPage=1&sqlId=COMMON_SSE_ZQPZ_GPLB_CP_GPLB_L"
)

US_EXCLUDED_TICKERS = {
    # Yahoo/常见免费源在当前环境中长期不可用，剔除后由后续成分补位，保持 US 样本总量不变。
    "FI",
    "IPG",
    "K",
}


@dataclass
class UniverseRow:
    ticker: str
    market: str
    name: str
    sector: str
    liquidity_tag: str
    included_reason: str
    note: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建 A/HK/US 三市场核心股票池（默认 300/200/300）")
    parser.add_argument(
        "--output-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.universe_core_3markets.csv",
        help="核心股票池输出文件",
    )
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.universe_3markets.csv",
        help="旧股票池锚点（优先保留）",
    )
    parser.add_argument("--a-limit", type=int, default=300, help="A 股核心池规模")
    parser.add_argument("--hk-limit", type=int, default=200, help="港股核心池规模")
    parser.add_argument("--us-limit", type=int, default=300, help="美股核心池规模")
    return parser.parse_args()


def infer_market_from_ticker(ticker: str) -> str:
    value = str(ticker or "").strip().upper()
    if value.endswith((".SS", ".SZ")):
        return "A"
    if value.endswith(".HK"):
        return "HK"
    return "US"


def load_seed_rows(path: Path) -> List[UniverseRow]:
    if not path.exists():
        return []
    rows: List[UniverseRow] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            market = infer_market_from_ticker(ticker)
            name = str(row.get("name") or ticker).strip()
            sector = str(row.get("sector") or "Unknown").strip()
            note = str(row.get("note") or f"{market} seed").strip()
            rows.append(
                UniverseRow(
                    ticker=ticker,
                    market=market,
                    name=name,
                    sector=sector if sector else "Unknown",
                    liquidity_tag="seed_anchor",
                    included_reason="legacy_universe_anchor",
                    note=note,
                )
            )
    return rows


def build_us_pool(limit: int) -> List[UniverseRow]:
    df = pd.read_csv(US_SP500_URL)
    rows: List[UniverseRow] = []
    for _, item in df.iterrows():
        symbol = str(item.get("Symbol") or "").strip().upper()
        if not symbol:
            continue
        if symbol in US_EXCLUDED_TICKERS:
            continue
        name = str(item.get("Security") or symbol).strip()
        sector = str(item.get("GICS Sector") or "Unknown").strip()
        rows.append(
            UniverseRow(
                ticker=symbol,
                market="US",
                name=name,
                sector=sector if sector else "Unknown",
                liquidity_tag="sp500_core",
                included_reason="S&P500 constituent",
                note="US core | S&P500 constituent",
            )
        )
        if len(rows) >= limit:
            break
    return rows


def _format_a_ticker(code: str, exchange: str) -> str:
    code_value = str(code).strip()
    if exchange and "深圳" in exchange:
        return f"{code_value}.SZ"
    if exchange and "上海" in exchange:
        return f"{code_value}.SS"
    if code_value.startswith(("0", "3", "2")):
        return f"{code_value}.SZ"
    return f"{code_value}.SS"


def build_a_pool(limit: int) -> List[UniverseRow]:
    # 优先用中证官方成分权重，保证“高流动”口径更稳
    try:
        import akshare as ak

        df = ak.index_stock_cons_weight_csindex(symbol="000300")
        df = df.sort_values(by="权重", ascending=False).reset_index(drop=True)
        rows: List[UniverseRow] = []
        for _, item in df.iterrows():
            code = str(item.get("成分券代码") or "").strip()
            if len(code) != 6 or not code.isdigit():
                continue
            name = str(item.get("成分券名称") or code).strip()
            exchange = str(item.get("交易所") or "").strip()
            weight = float(item.get("权重") or 0.0)
            ticker = _format_a_ticker(code, exchange)
            rows.append(
                UniverseRow(
                    ticker=ticker,
                    market="A",
                    name=name,
                    sector="Unknown",
                    liquidity_tag="csi300_constituent",
                    included_reason=f"CSI300 constituent (weight={weight:.3f}%)",
                    note=f"A core | CSI300 constituent | weight={weight:.3f}%",
                )
            )
            if len(rows) >= limit:
                break
        if rows:
            return rows
    except Exception:  # noqa: BLE001
        pass

    # 回退：仅上交所列表，维持可用性
    response = requests.get(
        SSE_STOCK_LIST_URL,
        headers={"Referer": "http://www.sse.com.cn", "User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    source_rows = payload.get("result") or []
    rows: List[UniverseRow] = []
    for item in source_rows:
        code = str(item.get("SECURITY_CODE_A") or "").strip()
        if len(code) != 6 or not code.isdigit():
            continue
        name = str(item.get("SECURITY_ABBR_A") or code).strip()
        rows.append(
            UniverseRow(
                ticker=f"{code}.SS",
                market="A",
                name=name,
                sector="Unknown",
                liquidity_tag="sse_listed_fallback",
                included_reason="SSE listed fallback (CSI300 source unavailable)",
                note="A core | SSE fallback",
            )
        )
        if len(rows) >= limit:
            break
    return rows


def _normalize_hk_table(df_raw: pd.DataFrame) -> pd.DataFrame:
    header_index = None
    first_col = df_raw.iloc[:, 0].astype(str)
    for idx, value in first_col.items():
        if str(value).strip().lower() == "stock code":
            header_index = idx
            break
    if header_index is None:
        raise ValueError("HKEX securities list header not found")

    header = [str(v).strip() for v in df_raw.iloc[header_index].tolist()]
    table = df_raw.iloc[header_index + 1 :].copy()
    table.columns = header
    return table


def _first_match_column(columns: Iterable[str], candidates: Iterable[str]) -> str:
    normalized = {str(col).strip().lower(): str(col).strip() for col in columns}
    for key in candidates:
        if key in normalized:
            return normalized[key]
    for col in columns:
        text = str(col).strip().lower()
        for key in candidates:
            if key in text:
                return str(col).strip()
    raise ValueError(f"required column missing: {','.join(candidates)}")


def build_hk_pool(limit: int) -> List[UniverseRow]:
    raw = pd.read_excel(HKEX_SECURITIES_URL, header=None)
    table = _normalize_hk_table(raw)

    code_col = _first_match_column(table.columns, ["stock code"])
    name_col = _first_match_column(table.columns, ["name of securities"])
    category_col = _first_match_column(table.columns, ["category"])
    sub_category_col = _first_match_column(table.columns, ["sub-category"])
    shortsell_col = _first_match_column(table.columns, ["shortsell eligible"])
    cas_col = _first_match_column(table.columns, ["cas eligible"])
    currency_col = _first_match_column(table.columns, ["trading currency"])

    frame = table[
        [
            code_col,
            name_col,
            category_col,
            sub_category_col,
            shortsell_col,
            cas_col,
            currency_col,
        ]
    ].copy()

    frame[code_col] = frame[code_col].astype(str).str.strip()
    frame = frame[frame[code_col].str.match(r"^\d{1,5}$", na=False)]
    frame[category_col] = frame[category_col].astype(str).str.strip()
    frame[sub_category_col] = frame[sub_category_col].astype(str).str.strip()
    frame[currency_col] = frame[currency_col].astype(str).str.strip()

    frame = frame[
        (frame[category_col] == "Equity")
        & (frame[sub_category_col].str.contains("Main Board", na=False))
        & (frame[currency_col] == "HKD")
    ].copy()

    frame[shortsell_col] = frame[shortsell_col].astype(str).str.strip().str.upper()
    frame[cas_col] = frame[cas_col].astype(str).str.strip().str.upper()
    frame["__code_int"] = frame[code_col].astype(int)
    frame["__priority"] = frame[shortsell_col].map(lambda v: 0 if v == "Y" else 1)
    frame["__priority2"] = frame[cas_col].map(lambda v: 0 if v == "Y" else 1)
    frame = frame.sort_values(by=["__priority", "__priority2", "__code_int"]).reset_index(drop=True)

    rows: List[UniverseRow] = []
    for _, item in frame.iterrows():
        code = str(item.get(code_col) or "").strip()
        if not code:
            continue
        ticker = f"{int(code):05d}.HK"
        name = str(item.get(name_col) or ticker).strip()
        shortsell = str(item.get(shortsell_col) or "").strip().upper() == "Y"
        tag = "hk_shortsell_eligible" if shortsell else "hk_main_board"
        reason = (
            "HK main board equity + shortsell eligible"
            if shortsell
            else "HK main board equity (non-shortsell)"
        )
        rows.append(
            UniverseRow(
                ticker=ticker,
                market="HK",
                name=name,
                sector="Unknown",
                liquidity_tag=tag,
                included_reason=reason,
                note=f"HK core | {reason}",
            )
        )
        if len(rows) >= limit:
            break
    return rows


def apply_seed_anchors(
    source_rows: List[UniverseRow], seed_rows: List[UniverseRow], market: str, limit: int
) -> List[UniverseRow]:
    rows_by_ticker: Dict[str, UniverseRow] = {row.ticker: row for row in source_rows}
    selected: List[UniverseRow] = []
    seen: set[str] = set()

    for seed in seed_rows:
        if seed.market != market:
            continue
        if seed.ticker in seen:
            continue
        picked = rows_by_ticker.get(seed.ticker, seed)
        selected.append(picked)
        seen.add(seed.ticker)
        if len(selected) >= limit:
            return selected

    for row in source_rows:
        if row.ticker in seen:
            continue
        selected.append(row)
        seen.add(row.ticker)
        if len(selected) >= limit:
            break

    return selected


def write_csv(path: Path, rows: List[UniverseRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticker",
        "market",
        "name",
        "sector",
        "liquidity_tag",
        "included_reason",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "ticker": row.ticker,
                    "market": row.market,
                    "name": row.name,
                    "sector": row.sector,
                    "liquidity_tag": row.liquidity_tag,
                    "included_reason": row.included_reason,
                    "note": row.note,
                }
            )


def main() -> None:
    args = parse_args()
    seed_rows = load_seed_rows(args.seed_file)

    us_rows = apply_seed_anchors(build_us_pool(args.us_limit), seed_rows, "US", args.us_limit)
    hk_rows = apply_seed_anchors(build_hk_pool(args.hk_limit), seed_rows, "HK", args.hk_limit)
    a_rows = apply_seed_anchors(build_a_pool(args.a_limit), seed_rows, "A", args.a_limit)

    combined = a_rows + hk_rows + us_rows
    write_csv(args.output_file, combined)

    summary = {
        "output_file": str(args.output_file),
        "market_counts": {
            "A": len(a_rows),
            "HK": len(hk_rows),
            "US": len(us_rows),
            "total": len(combined),
        },
        "sources": {
            "A": "akshare.index_stock_cons_weight_csindex(000300) with SSE fallback",
            "HK": "HKEX ListOfSecurities.xlsx (Main Board Equity + HKD + shortsell priority)",
            "US": "datasets/s-and-p-500-companies",
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
