#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEC_USER_AGENT = "investor-method-lab/1.0 (contact: research@example.com)"
SEC_REQUEST_INTERVAL_SECONDS = 0.2
SEC_RETRY_ATTEMPTS = 3

THIRTEEN_F_CIK_BY_INVESTOR: Dict[str, str] = {
    "warren_buffett": "0001067983",  # Berkshire Hathaway Inc.
    "bill_ackman": "0001336528",  # Pershing Square Capital Management, L.P.
    "dan_loeb": "0001040273",  # Third Point LLC
    "charlie_munger": "0000783412",  # Daily Journal Corp
}

ASSET_MATCH_RULES: Dict[str, Dict[str, List[str]]] = {
    "warren_buffett": {
        "Apple": ["APPLE INC"],
        "American Express": ["AMERICAN EXPRESS"],
        "Bank of America": ["BANK OF AMERICA"],
        "Coca-Cola": ["COCA COLA", "COCA-COLA"],
        "Chevron": ["CHEVRON"],
        "Occidental": ["OCCIDENTAL PETE", "OCCIDENTAL"],
    },
    "bill_ackman": {
        "Hilton": ["HILTON WORLDWIDE", "HILTON"],
        "Chipotle": ["CHIPOTLE MEXICAN GRILL", "CHIPOTLE"],
        "Lowe": ["LOWE'S COS", "LOWES COS", "LOWE'S", "LOWES"],
        "Universal Music Group": ["UNIVERSAL MUSIC"],
        "Restaurant Brands": ["RESTAURANT BRANDS"],
    },
    "dan_loeb": {
        "Alibaba": ["ALIBABA"],
        "Sony": ["SONY"],
        "Yahoo": ["YAHOO"],
        "Amazon/Microsoft": ["AMAZON COM", "MICROSOFT"],
    },
    "charlie_munger": {
        "Costco": ["COSTCO"],
        "BYD": ["BYD"],
        "Daily Journal": ["DAILY JOURNAL"],
    },
}

UNKNOWN_WEIGHT_NOTE = (
    "未披露/不适用（该持仓通常不在13F口径，或无公开单票占比）"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="为 Top20 投资人持仓补充占比字段（优先 SEC 13F 可核验口径）"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "top20_global_investors_10y_plus_calibrated.json",
        help="输入 JSON 文件",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "top20_global_investors_10y_plus_calibrated.json",
        help="输出 JSON 文件（默认覆盖输入）",
    )
    return parser.parse_args()


def http_get(url: str) -> bytes:
    last_error: Optional[Exception] = None
    for attempt in range(SEC_RETRY_ATTEMPTS):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": SEC_USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001
            last_error = error
            time.sleep(0.6 * (attempt + 1))
    if last_error is None:
        raise RuntimeError(f"request failed: {url}")
    raise last_error


def http_get_json(url: str) -> Dict[str, Any]:
    return json.loads(http_get(url).decode("utf-8"))


def http_get_text(url: str) -> str:
    return http_get(url).decode("utf-8", errors="ignore")


def normalize_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def first_child_text(element: ET.Element, tag_name: str) -> str:
    for child in element:
        if normalize_tag(child.tag) == tag_name:
            return (child.text or "").strip()
    return ""


def find_latest_13f(cik: str) -> Optional[Tuple[str, str]]:
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = http_get_json(submissions_url)
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    report_dates = recent.get("reportDate", [])

    for form, accession, report_date in zip(forms, accessions, report_dates):
        if form == "13F-HR":
            return accession, report_date
    return None


def find_infotable_filename(index_payload: Dict[str, Any]) -> Optional[str]:
    directory = index_payload.get("directory", {})
    items = directory.get("item", [])
    for item in items:
        name = str(item.get("name", ""))
        lowered = name.lower()
        if lowered.endswith(".xml") and "info" in lowered:
            return name
    for item in items:
        name = str(item.get("name", ""))
        lowered = name.lower()
        if lowered.endswith(".xml"):
            return name
    return None


def parse_13f_holdings(xml_text: str) -> List[Tuple[str, float]]:
    root = ET.fromstring(xml_text)
    aggregated: Dict[str, float] = {}

    for info_table in root.iter():
        if normalize_tag(info_table.tag) != "infoTable":
            continue
        issuer = first_child_text(info_table, "nameOfIssuer").upper()
        value_text = first_child_text(info_table, "value")
        if not issuer or not value_text:
            continue
        try:
            value = float(value_text)
        except ValueError:
            continue
        aggregated[issuer] = aggregated.get(issuer, 0.0) + value
    return list(aggregated.items())


def fetch_13f_snapshot(cik: str) -> Optional[Dict[str, Any]]:
    latest = find_latest_13f(cik)
    time.sleep(SEC_REQUEST_INTERVAL_SECONDS)
    if not latest:
        return None

    accession, report_date = latest
    accession_no_dash = accession.replace("-", "")
    cik_numeric = str(int(cik))
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession_no_dash}/index.json"
    index_payload = http_get_json(index_url)
    time.sleep(SEC_REQUEST_INTERVAL_SECONDS)

    infotable_name = find_infotable_filename(index_payload)
    if not infotable_name:
        return None

    xml_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/"
        f"{accession_no_dash}/{infotable_name}"
    )
    xml_text = http_get_text(xml_url)
    time.sleep(SEC_REQUEST_INTERVAL_SECONDS)
    holdings = parse_13f_holdings(xml_text)
    if not holdings:
        return None

    total_value = sum(value for _, value in holdings)
    if total_value <= 0:
        return None

    return {
        "accession": accession,
        "report_date": report_date,
        "total_value_kusd": total_value,
        "holdings": holdings,
    }


def match_weight_pct(
    investor_id: str, asset_name: str, holdings: Iterable[Tuple[str, float]]
) -> Optional[float]:
    rules = ASSET_MATCH_RULES.get(investor_id, {})
    candidate_keywords: List[str] = []
    for key, keywords in rules.items():
        if key.lower() in asset_name.lower():
            candidate_keywords = keywords
            break

    if not candidate_keywords:
        return None

    matched_total = 0.0
    for issuer, value in holdings:
        if any(keyword in issuer for keyword in candidate_keywords):
            matched_total += value

    if matched_total <= 0:
        return None
    return matched_total


def enrich_investor_holdings(
    investor: Dict[str, Any], sec_snapshot: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    item = dict(investor)
    holdings = list(item.get("representative_holdings", []))

    weighted: List[Dict[str, Any]] = []
    total_value = 0.0
    sec_holdings: List[Tuple[str, float]] = []
    report_date = None
    accession = None
    if sec_snapshot:
        total_value = float(sec_snapshot.get("total_value_kusd", 0.0))
        sec_holdings = list(sec_snapshot.get("holdings", []))
        report_date = sec_snapshot.get("report_date")
        accession = sec_snapshot.get("accession")

    for asset in holdings:
        entry: Dict[str, Any] = {
            "asset": asset,
            "weight_pct": None,
            "weight_text": "未披露/不适用",
            "weight_note": UNKNOWN_WEIGHT_NOTE,
            "weight_as_of": None,
            "weight_basis": "公开资料口径",
            "weight_source": None,
        }

        if sec_snapshot and total_value > 0 and sec_holdings:
            matched_value = match_weight_pct(item.get("id", ""), asset, sec_holdings)
            if matched_value is not None:
                weight_pct = (matched_value / total_value) * 100
                entry["weight_pct"] = round(weight_pct, 2)
                entry["weight_text"] = f"{weight_pct:.2f}%"
                entry["weight_note"] = (
                    "可核验：SEC 13F-HR 市值占比（仅美国长仓股票口径）"
                )
                entry["weight_as_of"] = report_date
                entry["weight_basis"] = "SEC 13F-HR 市值占比（美国长仓股票口径）"
                entry["weight_source"] = (
                    f"SEC 13F-HR {accession}" if accession else "SEC 13F-HR"
                )
            else:
                entry["weight_text"] = "13F未命中"
                entry["weight_note"] = (
                    "在最新13F未命中该资产（可能为历史仓位、非美股或策略头寸）"
                )
                entry["weight_as_of"] = report_date
                entry["weight_basis"] = "SEC 13F-HR 对齐结果"
                entry["weight_source"] = (
                    f"SEC 13F-HR {accession}" if accession else "SEC 13F-HR"
                )

        weighted.append(entry)

    item["representative_holdings_with_weight"] = weighted
    return item


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()
    payload = load_json(args.input)

    snapshots: Dict[str, Optional[Dict[str, Any]]] = {}
    for investor_id, cik in THIRTEEN_F_CIK_BY_INVESTOR.items():
        try:
            snapshots[investor_id] = fetch_13f_snapshot(cik)
        except Exception as error:  # noqa: BLE001
            print(f"[WARN] 拉取 {investor_id} 的 13F 失败: {error}")
            snapshots[investor_id] = None

    enriched = []
    matched_weights = 0
    total_weight_rows = 0
    for investor in payload.get("investors", []):
        investor_id = investor.get("id", "")
        sec_snapshot = snapshots.get(investor_id)
        updated = enrich_investor_holdings(investor, sec_snapshot)
        for row in updated.get("representative_holdings_with_weight", []):
            total_weight_rows += 1
            if row.get("weight_pct") is not None:
                matched_weights += 1
        enriched.append(updated)

    payload["investors"] = enriched
    payload["holdings_weight_coverage_note"] = (
        "占比优先采用 SEC 13F-HR 最新报告市值占比（仅美国长仓股票口径）；"
        "宏观/期货/非美股/历史仓位常无对应单票披露，统一标注为未披露或13F未命中。"
    )
    payload["holdings_weight_last_updated"] = time.strftime("%Y-%m-%d")

    dump_json(args.output, payload)
    print(f"已写入: {args.output}")
    print(f"占比命中: {matched_weights}/{total_weight_rows}")


if __name__ == "__main__":
    main()
