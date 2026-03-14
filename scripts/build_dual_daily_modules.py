#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOCUS_FILE = PROJECT_ROOT / "data" / "dcf_special_focus_list.json"
DEFAULT_DCF_TARGETS_CANDIDATES = [
    PROJECT_ROOT.parent / "hit-zone" / "data" / "parameter_targets.json",
    PROJECT_ROOT.parent / "dcf-suite" / "data" / "parameter_targets.json",
]
TOP_FILE_CANDIDATES = [
    PROJECT_ROOT / "output" / "top20_first_batch_opportunities_real_3markets.csv",
    PROJECT_ROOT / "output" / "top20_first_batch_opportunities_real.csv",
    PROJECT_ROOT / "output" / "top20_first_batch_opportunities.csv",
]
REAL_FILE_CANDIDATES = [
    PROJECT_ROOT / "data" / "opportunities.real_3markets.csv",
    PROJECT_ROOT / "data" / "opportunities.real.csv",
    PROJECT_ROOT / "data" / "opportunities.sample.csv",
]
META_FILE_CANDIDATES = [
    PROJECT_ROOT / "docs" / "opportunities_real_data_meta_3markets.json",
    PROJECT_ROOT / "docs" / "opportunities_real_data_meta.json",
]


@dataclass
class FocusItem:
    dcf_symbol: str
    ticker: str
    name: str
    tag: str


def resolve_default_dcf_targets_file() -> Path:
    for path in DEFAULT_DCF_TARGETS_CANDIDATES:
        if path.exists():
            return path
    return DEFAULT_DCF_TARGETS_CANDIDATES[0]


DEFAULT_DCF_TARGETS_FILE = resolve_default_dcf_targets_file()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build split daily modules: DCF special-focus list + opportunity mining list."
    )
    parser.add_argument(
        "--focus-file",
        type=Path,
        default=DEFAULT_FOCUS_FILE,
        help="JSON file for manually curated DCF special-focus symbols.",
    )
    parser.add_argument(
        "--dcf-parameter-targets-file",
        type=Path,
        default=DEFAULT_DCF_TARGETS_FILE,
        help="Fallback file when focus file is missing.",
    )
    parser.add_argument(
        "--top-file",
        type=Path,
        default=None,
        help="Top opportunities csv (default auto-detect).",
    )
    parser.add_argument(
        "--real-file",
        type=Path,
        default=None,
        help="Real opportunities csv used for ticker-level market fields (default auto-detect).",
    )
    parser.add_argument(
        "--meta-file",
        type=Path,
        default=None,
        help="Real-data meta json (default auto-detect).",
    )
    parser.add_argument("--as-of-date", default="", help="Override as-of date (YYYY-MM-DD).")
    parser.add_argument(
        "--opportunity-top",
        type=int,
        default=10,
        help="Number of opportunity rows to output after removing focus names.",
    )
    parser.add_argument(
        "--message-top",
        type=int,
        default=8,
        help="Number of lines kept in each push module message.",
    )
    parser.add_argument(
        "--output-focus-md",
        type=Path,
        default=PROJECT_ROOT / "docs" / "dcf_special_focus_daily.md",
        help="Output markdown for DCF special-focus module.",
    )
    parser.add_argument(
        "--output-opportunity-md",
        type=Path,
        default=PROJECT_ROOT / "docs" / "opportunity_mining_daily.md",
        help="Output markdown for opportunity mining module.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "docs" / "daily_dual_modules.json",
        help="Output JSON for downstream message delivery.",
    )
    return parser.parse_args()


def first_existing(candidates: List[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


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


def normalize_ticker(raw: str) -> str:
    return str(raw or "").strip().upper()


def ticker_lookup_keys(raw: str) -> List[str]:
    ticker = normalize_ticker(raw)
    if not ticker:
        return []

    keys: List[str] = []

    def add(value: str) -> None:
        normalized = normalize_ticker(value)
        if normalized and normalized not in keys:
            keys.append(normalized)

    add(ticker)
    if ticker.endswith(".HK"):
        code = ticker[:-3]
        if code.isdigit():
            add(f"{int(code)}.HK")
            add(f"{int(code):05d}.HK")
            add(f"HK.{int(code)}")
            add(f"HK.{int(code):05d}")
    elif ticker.endswith(".SS"):
        code = ticker[:-3]
        if code.isdigit():
            add(f"SH.{code}")
    elif ticker.endswith(".SZ"):
        code = ticker[:-3]
        if code.isdigit():
            add(f"SZ.{code}")
    elif ticker.startswith(("US.", "HK.", "SH.", "SZ.")):
        add(dcf_symbol_to_ticker(ticker))
    else:
        add(f"US.{ticker}")
    return keys


def dcf_symbol_to_ticker(dcf_symbol: str) -> str:
    raw = str(dcf_symbol or "").strip().upper()
    if not raw or "." not in raw:
        return raw
    market, code = raw.split(".", 1)
    code = code.strip()
    if market == "US":
        return code
    if market == "HK":
        try:
            hk_num = int(code)
            return f"{hk_num:04d}.HK"
        except ValueError:
            return f"{code}.HK"
    if market == "SH":
        return f"{code}.SS"
    if market == "SZ":
        return f"{code}.SZ"
    return raw


def parse_note_fields(note: str) -> Dict[str, float]:
    fields: Dict[str, float] = {}
    text = str(note or "")
    for key, raw in re.findall(r"\b(close|target|upside)=([-+]?\d+(?:\.\d+)?)%?", text):
        try:
            fields[key] = float(raw)
        except ValueError:
            continue
    return fields


def fmt_float(value: float | None, digits: int = 2, default: str = "-") -> str:
    if value is None:
        return default
    return f"{value:.{digits}f}"


def fmt_pct(value: float | None, digits: int = 2, default: str = "-") -> str:
    if value is None:
        return default
    return f"{value * 100:.{digits}f}%"


def load_focus_items(focus_file: Path, dcf_targets_file: Path) -> List[FocusItem]:
    payload: Any = None
    source = ""
    if focus_file.exists():
        payload = read_json(focus_file)
        source = "focus_file"
    elif dcf_targets_file.exists():
        payload = read_json(dcf_targets_file)
        source = "dcf_parameter_targets"
    else:
        payload = []

    if isinstance(payload, dict):
        raw_items = payload.get("symbols", [])
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raw_items = []

    out: List[FocusItem] = []
    seen: set[str] = set()
    for raw in raw_items:
        if isinstance(raw, str):
            dcf_symbol = raw.strip().upper()
            ticker = dcf_symbol_to_ticker(dcf_symbol)
            name = dcf_symbol
            tag = "deep_calibrated"
        elif isinstance(raw, dict):
            dcf_symbol = str(raw.get("dcf_symbol") or raw.get("symbol") or "").strip().upper()
            ticker = normalize_ticker(str(raw.get("ticker") or dcf_symbol_to_ticker(dcf_symbol)))
            name = str(raw.get("name") or raw.get("name_cn") or ticker or dcf_symbol).strip()
            tag = str(raw.get("tag") or "deep_calibrated").strip() or "deep_calibrated"
        else:
            continue

        if not dcf_symbol and ticker:
            dcf_symbol = ticker
        if not ticker:
            ticker = dcf_symbol_to_ticker(dcf_symbol)
        if not dcf_symbol and not ticker:
            continue

        key = f"{dcf_symbol}|{ticker}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            FocusItem(
                dcf_symbol=dcf_symbol,
                ticker=ticker,
                name=name,
                tag=tag if source == "focus_file" else f"{tag}:{source}",
            )
        )
    return out


def infer_as_of_date(meta_file: Path | None, fallback: str = "") -> str:
    if fallback:
        return fallback
    if meta_file and meta_file.exists():
        payload = read_json(meta_file)
        dates = payload.get("as_of_dates") or []
        if isinstance(dates, list) and dates:
            return str(dates[-1])
    return datetime.now().strftime("%Y-%m-%d")


def build_focus_rows(
    focus_items: List[FocusItem], real_map: Dict[str, Dict[str, str]]
) -> tuple[List[Dict[str, Any]], List[FocusItem]]:
    rows: List[Dict[str, Any]] = []
    missing: List[FocusItem] = []
    for item in focus_items:
        row = None
        for key in ticker_lookup_keys(item.ticker) + ticker_lookup_keys(item.dcf_symbol):
            row = real_map.get(key)
            if row is not None:
                break
        if row is None:
            missing.append(item)
            continue
        note_fields = parse_note_fields(row.get("note", ""))
        close = (
            as_float(row.get("dcf_price"))
            or note_fields.get("close")
            or as_float(row.get("price"))
            or as_float(row.get("close"))
        )
        iv = as_float(row.get("dcf_iv_base")) or as_float(row.get("target_mean_price")) or as_float(
            row.get("fair_value")
        )
        mos = as_float(row.get("dcf_mos_base"))
        if mos is None and close is not None and iv not in (None, 0.0):
            mos = (iv - close) / iv

        rows.append(
            {
                "name": row.get("name") or item.name,
                "ticker": item.ticker,
                "dcf_symbol": item.dcf_symbol,
                "tag": item.tag,
                "close": close,
                "iv": iv,
                "mos": mos,
                "status": row.get("dcf_status") or "",
            }
        )
    rows.sort(key=lambda x: as_float(x.get("mos")) or -9.0, reverse=True)
    return rows, missing


def build_opportunity_rows(
    top_rows: List[Dict[str, str]],
    focus_tickers: set[str],
    top_n: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in top_rows:
        ticker = normalize_ticker(raw.get("ticker", ""))
        if not ticker or ticker in focus_tickers:
            continue
        note = raw.get("note", "")
        note_fields = parse_note_fields(note)
        rows.append(
            {
                "ticker": ticker,
                "name": raw.get("name", ticker),
                "market": raw.get("market", ""),
                "score": as_float(raw.get("composite_score")),
                "mos_pct": as_float(raw.get("margin_of_safety")),
                "best_group": raw.get("best_group", ""),
                "close": note_fields.get("close"),
                "target": note_fields.get("target"),
            }
        )
    rows.sort(key=lambda x: x.get("score") or -9.0, reverse=True)
    return rows[:max(0, top_n)]


def build_focus_message(
    rows: List[Dict[str, Any]],
    missing: List[FocusItem],
    focus_total: int,
    as_of_date: str,
    top_n: int,
) -> tuple[str, List[str]]:
    title = f"【特别关注｜深度DCF校准】{as_of_date}"
    lines = [
        f"口径：逐公司校准清单（{focus_total}只）",
        f"命中行情覆盖：{len(rows)}/{focus_total}",
    ]
    for idx, row in enumerate(rows[:top_n], start=1):
        lines.append(
            (
                f"{idx}. {row['name']}({row['dcf_symbol']}) "
                f"MOS {fmt_pct(as_float(row.get('mos')))} | "
                f"现价 {fmt_float(as_float(row.get('close')))} | "
                f"中性 {fmt_float(as_float(row.get('iv')))}"
            )
        )
    if missing:
        preview = ", ".join(item.dcf_symbol for item in missing[:4])
        suffix = "..." if len(missing) > 4 else ""
        lines.append(f"待补数据：{preview}{suffix}")
    return title, lines


def build_opportunity_message(
    rows: List[Dict[str, Any]],
    as_of_date: str,
    top_n: int,
) -> tuple[str, List[str]]:
    title = f"【机会挖掘｜新增候选】{as_of_date}"
    lines = [
        "口径：机会池剔除特别关注标的后按综合分排序",
        f"本次展示：{min(len(rows), top_n)}只",
    ]
    for idx, row in enumerate(rows[:top_n], start=1):
        close = fmt_float(as_float(row.get("close")))
        target = fmt_float(as_float(row.get("target")))
        lines.append(
            (
                f"{idx}. {row['name']}({row['ticker']}) "
                f"分数 {fmt_float(as_float(row.get('score')), 1)} | "
                f"MOS {fmt_float(as_float(row.get('mos_pct')), 1)}% | "
                f"现价/目标 {close}/{target}"
            )
        )
    return title, lines


def build_focus_markdown(
    title: str,
    as_of_date: str,
    rows: List[Dict[str, Any]],
    missing: List[FocusItem],
    focus_total: int,
    source_file: Path,
) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- 日期：{as_of_date}")
    lines.append(f"- 来源：`{source_file}`")
    lines.append(f"- 覆盖：{len(rows)}/{focus_total}")
    lines.append("")
    lines.append("| # | 标的 | DCF符号 | 安全边际 | 现价 | 中性估值 |")
    lines.append("|---|---|---|---:|---:|---:|")
    for idx, row in enumerate(rows, start=1):
        lines.append(
            "| {idx} | {name}({ticker}) | {dcf_symbol} | {mos} | {close} | {iv} |".format(
                idx=idx,
                name=row["name"],
                ticker=row["ticker"],
                dcf_symbol=row["dcf_symbol"],
                mos=fmt_pct(as_float(row.get("mos"))),
                close=fmt_float(as_float(row.get("close"))),
                iv=fmt_float(as_float(row.get("iv"))),
            )
        )
    if missing:
        lines.append("")
        lines.append("## 待补行情")
        for item in missing:
            lines.append(f"- {item.name}（{item.dcf_symbol} / {item.ticker}）")
    return "\n".join(lines) + "\n"


def build_opportunity_markdown(
    title: str,
    as_of_date: str,
    rows: List[Dict[str, Any]],
    source_file: Path,
) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- 日期：{as_of_date}")
    lines.append(f"- 来源：`{source_file}`")
    lines.append(f"- 数量：{len(rows)}")
    lines.append("")
    lines.append("| # | 标的 | 综合分 | MOS | 最优方法论 | 现价 | 目标价 |")
    lines.append("|---|---|---:|---:|---|---:|---:|")
    for idx, row in enumerate(rows, start=1):
        lines.append(
            "| {idx} | {name}({ticker}) | {score} | {mos} | {group} | {close} | {target} |".format(
                idx=idx,
                name=row["name"],
                ticker=row["ticker"],
                score=fmt_float(as_float(row.get("score")), 2),
                mos=fmt_float(as_float(row.get("mos_pct")), 1, default="-") + "%",
                group=row.get("best_group") or "-",
                close=fmt_float(as_float(row.get("close"))),
                target=fmt_float(as_float(row.get("target"))),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()

    top_file = args.top_file or first_existing(TOP_FILE_CANDIDATES)
    real_file = args.real_file or first_existing(REAL_FILE_CANDIDATES)
    meta_file = args.meta_file or first_existing(META_FILE_CANDIDATES)
    if top_file is None:
        raise RuntimeError("top opportunities file not found")
    if real_file is None:
        raise RuntimeError("real opportunities file not found")

    focus_items = load_focus_items(
        focus_file=args.focus_file,
        dcf_targets_file=args.dcf_parameter_targets_file,
    )
    if not focus_items:
        raise RuntimeError("focus list is empty; check focus file or fallback targets file")

    top_rows = read_csv(top_file)
    real_rows = read_csv(real_file)
    real_map: Dict[str, Dict[str, str]] = {}
    for row in real_rows:
        ticker = row.get("ticker", "")
        dcf_symbol = row.get("dcf_symbol", "")
        for key in ticker_lookup_keys(ticker) + ticker_lookup_keys(dcf_symbol):
            real_map.setdefault(key, row)
    as_of_date = infer_as_of_date(meta_file=meta_file, fallback=args.as_of_date)

    focus_rows, missing_focus = build_focus_rows(focus_items=focus_items, real_map=real_map)
    focus_tickers = {item.ticker for item in focus_items}
    opportunity_rows = build_opportunity_rows(
        top_rows=top_rows,
        focus_tickers=focus_tickers,
        top_n=args.opportunity_top,
    )

    focus_title, focus_lines = build_focus_message(
        rows=focus_rows,
        missing=missing_focus,
        focus_total=len(focus_items),
        as_of_date=as_of_date,
        top_n=args.message_top,
    )
    opportunity_title, opportunity_lines = build_opportunity_message(
        rows=opportunity_rows,
        as_of_date=as_of_date,
        top_n=args.message_top,
    )

    args.output_focus_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_opportunity_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    args.output_focus_md.write_text(
        build_focus_markdown(
            title=focus_title,
            as_of_date=as_of_date,
            rows=focus_rows,
            missing=missing_focus,
            focus_total=len(focus_items),
            source_file=args.focus_file,
        ),
        encoding="utf-8",
    )
    args.output_opportunity_md.write_text(
        build_opportunity_markdown(
            title=opportunity_title,
            as_of_date=as_of_date,
            rows=opportunity_rows,
            source_file=top_file,
        ),
        encoding="utf-8",
    )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "as_of_date": as_of_date,
        "inputs": {
            "focus_file": str(args.focus_file),
            "top_file": str(top_file),
            "real_file": str(real_file),
            "meta_file": str(meta_file) if meta_file else "",
        },
        "outputs": {
            "focus_markdown": str(args.output_focus_md),
            "opportunity_markdown": str(args.output_opportunity_md),
        },
        "focus_module": {
            "title": focus_title,
            "summary": {
                "focus_total": len(focus_items),
                "covered": len(focus_rows),
                "missing": len(missing_focus),
            },
            "rows": focus_rows,
            "missing_rows": [
                {
                    "dcf_symbol": item.dcf_symbol,
                    "ticker": item.ticker,
                    "name": item.name,
                    "tag": item.tag,
                }
                for item in missing_focus
            ],
            "message_lines": focus_lines,
        },
        "opportunity_module": {
            "title": opportunity_title,
            "summary": {
                "count": len(opportunity_rows),
                "excluded_focus_tickers": sorted(focus_tickers),
            },
            "rows": opportunity_rows,
            "message_lines": opportunity_lines,
        },
    }
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "focus_markdown": str(args.output_focus_md),
                "opportunity_markdown": str(args.output_opportunity_md),
                "json": str(args.output_json),
                "focus_total": len(focus_items),
                "focus_covered": len(focus_rows),
                "opportunity_count": len(opportunity_rows),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
