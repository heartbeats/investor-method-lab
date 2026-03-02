#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import socket
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yfinance as yf
import urllib.request
import urllib.parse

try:
    from futu import OpenQuoteContext, RET_OK
except Exception:  # noqa: BLE001
    OpenQuoteContext = None
    RET_OK = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]

QUOTE_TICKER_MAP: Dict[str, str] = {
    "BRK.B": "BRK-B",
}

ASSET_TICKER_HINTS: Dict[str, str] = {
    "apple": "AAPL",
    "american express": "AXP",
    "bank of america": "BAC",
    "coca-cola": "KO",
    "coca cola": "KO",
    "chevron": "CVX",
    "occidental petroleum": "OXY",
    "hilton": "HLT",
    "chipotle": "CMG",
    "lowe": "LOW",
    "universal music": "UMG.AS",
    "restaurant brands": "QSR",
    "alibaba": "BABA",
    "amazon": "AMZN",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "broadcom": "AVGO",
    "palo alto": "PANW",
    "tesla": "TSLA",
    "tencent": "0700.HK",
    "berkshire": "BRK-B",
    "alphabet": "GOOG",
    "east west bancorp": "EWBC",
    "coinbase": "COIN",
    "roku": "ROKU",
    "uipath": "PATH",
    "palantir": "PLTR",
    "trump media": "DJT",
    "costco": "COST",
    "byd": "1211.HK",
    "fiat chrysler": "STLA",
    "micron": "MU",
    "intel": "INTC",
    "synopsys": "SNPS",
    "coreweave": "CRWV",
    "nokia": "NOK",
    "nebius": "YNDX",
}

TICKER_NAME_CN: Dict[str, str] = {
    "AAPL": "苹果",
    "AXP": "美国运通",
    "BAC": "美国银行",
    "KO": "可口可乐",
    "CVX": "雪佛龙",
    "OXY": "西方石油",
    "HLT": "希尔顿",
    "CMG": "墨式烧烤",
    "LOW": "劳氏",
    "UMG.AS": "环球音乐集团",
    "QSR": "餐饮品牌国际",
    "BABA": "阿里巴巴",
    "AMZN": "亚马逊",
    "MSFT": "微软",
    "NVDA": "英伟达",
    "AVGO": "博通",
    "PANW": "帕洛阿尔托网络",
    "TSLA": "特斯拉",
    "0700.HK": "腾讯控股",
    "BRK-B": "伯克希尔·哈撒韦B",
    "GOOG": "谷歌",
    "GOOGL": "谷歌",
    "EWBC": "华美银行",
    "COIN": "Coinbase",
    "ROKU": "Roku",
    "PATH": "UiPath",
    "PLTR": "Palantir",
    "DJT": "特朗普媒体科技集团",
    "COST": "好市多",
    "1211.HK": "比亚迪股份",
    "STLA": "斯泰兰蒂斯",
    "MU": "美光科技",
    "INTC": "英特尔",
    "SNPS": "新思科技",
    "CRWV": "CoreWeave",
    "NOK": "诺基亚",
    "YNDX": "Nebius Group",
    "AMD": "超威半导体",
    "PDD": "拼多多",
    "SHOP": "Shopify",
    "HOOD": "Robinhood",
    "CRCL": "Circle",
    "TEM": "Tempus AI",
    "RBLX": "Roblox",
    "SQ": "Block",
    "U": "Unity",
    "TWLO": "Twilio",
    "CRSP": "CRISPR Therapeutics",
    "BEAM": "Beam Therapeutics",
    "TDOC": "Teladoc",
    "ZM": "Zoom",
    "RKT": "Rocket Companies",
    "CROX": "Crocs",
}

SEC_CIK_BY_INVESTOR: Dict[str, str] = {
    "warren_buffett": "0001067983",
    "bill_ackman": "0001336528",
    "dan_loeb": "0001040273",
    "charlie_munger": "0000783412",
    "joel_greenblatt": "0001510387",  # Gotham Asset Management, LLC
    "james_simons": "0001037389",  # Renaissance Technologies LLC
    "bruce_kovner": "0000872573",  # Caxton Associates LP
    "george_soros": "0001029160",  # Soros Fund Management LLC
    "stanley_druckenmiller": "0001536411",  # Duquesne Family Office LLC
    "steven_cohen": "0001603466",  # Point72 Asset Management, L.P.
    "paul_tudor_jones": "0000923093",  # Tudor Investment Corp et al
    "seth_klarman": "0001061768",  # Baupost Group LLC
    "howard_marks": "0000949509",  # Oaktree Capital Management LP
    "duan_yongping": "0001759760",  # H&H International Investment, LLC
    "li_lu": "0001709323",  # Himalaya Capital Management LLC
    "cathie_wood": "0001697748",  # ARK Investment Management LLC
    "jensen_huang": "0001045810",  # NVIDIA CORP (look-through indirect exposure)
}

DISCLOSURE_ENTITY_BY_INVESTOR: Dict[str, Dict[str, str]] = {
    "joel_greenblatt": {"entity_name": "Gotham Asset Management, LLC", "cik": "0001510387"},
    "james_simons": {"entity_name": "Renaissance Technologies LLC", "cik": "0001037389"},
    "bruce_kovner": {"entity_name": "Caxton Associates LP", "cik": "0000872573"},
    "george_soros": {"entity_name": "Soros Fund Management LLC", "cik": "0001029160"},
    "stanley_druckenmiller": {"entity_name": "Duquesne Family Office LLC", "cik": "0001536411"},
    "steven_cohen": {"entity_name": "Point72 Asset Management, L.P.", "cik": "0001603466"},
    "paul_tudor_jones": {"entity_name": "Tudor Investment Corp et al", "cik": "0000923093"},
    "seth_klarman": {"entity_name": "Baupost Group LLC", "cik": "0001061768"},
    "howard_marks": {"entity_name": "Oaktree Capital Management LP", "cik": "0000949509"},
    "duan_yongping": {"entity_name": "H&H International Investment, LLC", "cik": "0001759760"},
    "li_lu": {"entity_name": "Himalaya Capital Management LLC", "cik": "0001709323"},
    "cathie_wood": {"entity_name": "ARK Investment Management LLC", "cik": "0001697748"},
    "jensen_huang": {"entity_name": "NVIDIA CORP (间接敞口口径)", "cik": "0001045810"},
}

AUTO_POPULATE_HOLDINGS_FROM_13F: Dict[str, int] = {
    "joel_greenblatt": 8,
    "james_simons": 8,
    "bruce_kovner": 8,
    "george_soros": 8,
    "stanley_druckenmiller": 8,
    "steven_cohen": 8,
    "paul_tudor_jones": 8,
    "seth_klarman": 8,
    "howard_marks": 8,
    "duan_yongping": 8,
    "li_lu": 8,
    "cathie_wood": 8,
}

HYBRID_LOOKTHROUGH_13F_BY_INVESTOR: Dict[str, int] = {
    "jensen_huang": 5,  # 直接持股 + 英伟达公司13F间接敞口
}

SEC_ISSUER_KEYWORDS_BY_TICKER: Dict[str, List[str]] = {
    "AAPL": ["APPLE INC"],
    "AXP": ["AMERICAN EXPRESS"],
    "BAC": ["BANK OF AMERICA", "BK OF AMERICA"],
    "KO": ["COCA COLA", "COCA-COLA"],
    "CVX": ["CHEVRON"],
    "OXY": ["OCCIDENTAL PETE", "OCCIDENTAL PETROLEUM"],
    "HLT": ["HILTON WORLDWIDE", "HILTON"],
    "CMG": ["CHIPOTLE"],
    "LOW": ["LOWE'S", "LOWES"],
    "QSR": ["RESTAURANT BRANDS"],
    "BABA": ["ALIBABA"],
    "AMZN": ["AMAZON COM"],
    "MSFT": ["MICROSOFT"],
    "COST": ["COSTCO"],
    "BRK-B": ["BERKSHIRE HATHAWAY"],
    "GOOG": ["ALPHABET INC"],
    "GOOGL": ["ALPHABET INC"],
    "EWBC": ["EAST WEST BANCORP"],
    "NVDA": ["NVIDIA"],
    "PDD": ["PDD HOLDINGS"],
    "MU": ["MICRON TECHNOLOGY"],
    "CROX": ["CROCS"],
    "SHOP": ["SHOPIFY"],
    "U": ["UNITY SOFTWARE"],
    "AMD": ["ADVANCED MICRO DEVICES"],
    "HOOD": ["ROBINHOOD"],
    "RBLX": ["ROBLOX"],
    "CRSP": ["CRISPR THERAPEUTICS"],
    "INTC": ["INTEL CORP", "INTEL"],
    "SNPS": ["SYNOPSYS INC", "SYNOPSYS"],
    "CRWV": ["COREWEAVE INC", "COREWEAVE"],
    "NOK": ["NOKIA CORP", "NOKIA"],
    "YNDX": ["NEBIUS GROUP", "YANDEX"],
}

SEC_USER_AGENT = "investor-method-lab/1.0 (contact: research@example.com)"
SEC_REQUEST_INTERVAL_SECONDS = 0.2
WIKI_USER_AGENT = "investor-method-lab/1.0 (contact: research@example.com)"
THIRTEENF_INFO_USER_AGENT = "investor-method-lab/1.0 (contact: research@example.com)"
THIRTEENF_INFO_BASE = "https://13f.info"

THIRTEENF_TICKER_NORMALIZATION: Dict[str, str] = {
    "0A2S.IL": "PDD",
}

FUTU_OPEND_PORTS: Tuple[int, int] = (11112, 11111)

DEFAULT_INTRO_TEMPLATE = (
    "{name_cn}的公开投资特征为“{style}”。核心思路是“{thesis}”，"
    "当前页面展示为公开资料可见口径，非完整私有账户明细。"
)

PERSONAL_INTRO_OVERRIDES: Dict[str, str] = {
    "warren_buffett": "巴菲特是伯克希尔掌舵者，长期以“买入优秀公司并长期持有”的价值复利框架著称。",
    "charlie_munger": "芒格强调多学科思维与高质量企业长期持有，对“好公司+合理价格”框架影响深远。",
    "george_soros": "索罗斯以全球宏观与反身性框架闻名，擅长在宏观拐点做高弹性仓位配置。",
    "stanley_druckenmiller": "德鲁肯米勒强调“赔率+趋势+仓位纪律”，在宏观和成长赛道均有代表案例。",
    "peter_lynch": "彼得·林奇以“投资你了解的公司”著称，强调从产业和生活场景中发现成长股。",
}

INVESTOR_WIKI_TITLES: Dict[str, str] = {
    "peter_brandt": "Peter Brandt",
    "joel_greenblatt": "Joel Greenblatt",
    "james_simons": "Jim Simons (mathematician)",
    "george_soros": "George Soros",
    "stanley_druckenmiller": "Stanley Druckenmiller",
    "michael_steinhardt": "Michael Steinhardt",
    "steven_cohen": "Steven A. Cohen",
    "peter_lynch": "Peter Lynch",
    "leon_levy": "Leon Levy",
    "paul_tudor_jones": "Paul Tudor Jones",
    "mohnish_pabrai": "Mohnish Pabrai",
    "shelby_davis": "Shelby M. C. Davis",
    "bruce_kovner": "Bruce Kovner",
    "warren_buffett": "Warren Buffett",
    "howard_marks": "Howard Marks",
    "charlie_munger": "Charlie Munger",
    "seth_klarman": "Seth Klarman",
    "bill_ackman": "Bill Ackman",
    "walter_schloss": "Walter Schloss",
    "dan_loeb": "Dan Loeb",
    "duan_yongping": "Duan Yongping",
    "li_lu": "Li Lu (investor)",
    "nancy_pelosi": "Nancy Pelosi",
    "jensen_huang": "Jensen Huang",
    "cathie_wood": "Cathie Wood",
    "donald_trump": "Donald Trump",
    "marjorie_taylor_greene": "Marjorie Taylor Greene",
    "josh_gottheimer": "Josh Gottheimer",
    "gil_cisneros": "Gil Cisneros",
}

INVESTOR_AVATAR_OVERRIDES: Dict[str, str] = {
    # 公开投资人资料页面头像（用于补齐 Wikipedia 无缩略图的场景）
    "peter_brandt": "https://upload.wikimedia.org/wikipedia/commons/8/81/Peter_Brandt_%282024%29.jpg",
    "joel_greenblatt": "https://business.rice.edu/sites/default/files/uploads/headshots/Joel-Greenblatt.png",
    "bruce_kovner": "https://imageio.forbes.com/specials-images/imageserve/5d8a93eb6de3150009a501d1/0x0.jpg?format=jpg&crop=1053,1053,x9,y80,safe&height=416&width=416&fit=bounds",
    "stanley_druckenmiller": "https://imageio.forbes.com/specials-images/imageserve/5d8a9ea218444200084e6e8b/0x0.jpg?format=jpg&crop=2663,2661,x1229,y6,safe&height=416&width=416&fit=bounds",
    "peter_lynch": "https://upload.wikimedia.org/wikipedia/commons/4/48/PeterLynch-Books-Wide.jpg",
    "michael_steinhardt": "https://imageio.forbes.com/specials-images/imageserve/5c9e77ce4bbe6f04e11897d2/0x0.jpg?format=jpg&crop=2400,2399,x0,y95,safe&height=416&width=416&fit=bounds",
    "dan_loeb": "https://imageio.forbes.com/specials-images/imageserve/5d8b04349a9bdd00080fb12d/0x0.jpg?format=jpg&crop=2210,2211,x206,y39,safe&height=416&width=416&fit=bounds",
    "li_lu": "https://www.portfoliomoment.com/avatars/%E6%9D%8E%E5%BD%95.jpg",
    "duan_yongping": "https://www.portfoliomoment.com/avatars/%E6%AE%B5%E6%B0%B8%E5%B9%B3.jpg",
    "mohnish_pabrai": "https://www.portfoliomoment.com/avatars/%E8%8E%AB%E5%B0%BC%E4%BB%80.jpg",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建网页用投资者资料库（总览+详情）")
    parser.add_argument(
        "--base-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "top20_global_investors_10y_plus_calibrated.json",
        help="基础投资者数据（Top20 校准口径）",
    )
    parser.add_argument(
        "--additional-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "investor_additional_watchlist.json",
        help="补充关注名单",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "investor_profiles.json",
        help="输出资料库 JSON",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "cache" / "holding_prices",
        help="行情缓存目录",
    )
    parser.add_argument(
        "--cache-ttl-hours",
        type=int,
        default=24,
        help="行情缓存有效期（小时）",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用缓存，强制实时拉取行情",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def _cache_path(cache_dir: Path, ticker: str) -> Path:
    key = "".join(ch if ch.isalnum() else "_" for ch in ticker.upper())
    return cache_dir / f"{key}.json"


def _load_cached_quote(cache_file: Path, ttl_hours: int) -> Dict[str, Any] | None:
    if ttl_hours <= 0 or not cache_file.exists():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_at_raw = payload.get("cached_at_utc")
        quote = payload.get("quote")
        if not cached_at_raw or not isinstance(quote, dict):
            return None
        cached_at = datetime.fromisoformat(str(cached_at_raw))
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - cached_at > timedelta(hours=ttl_hours):
            return None
        return quote
    except Exception:  # noqa: BLE001
        return None


def _save_cached_quote(cache_file: Path, quote: Dict[str, Any]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at_utc": datetime.now(timezone.utc).isoformat(),
        "quote": quote,
    }
    cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_quote(ticker: str) -> Dict[str, Any] | None:
    yf_ticker = QUOTE_TICKER_MAP.get(ticker, ticker)
    ticker_obj = yf.Ticker(yf_ticker)
    history = ticker_obj.history(period="5d", interval="1d", auto_adjust=False)
    closes = history.get("Close")
    if closes is None or closes.dropna().empty:
        return None
    closes = closes.dropna()
    latest_price = float(closes.iloc[-1])
    latest_date = closes.index[-1].date().isoformat()
    currency = ticker_obj.fast_info.get("currency") if ticker_obj.fast_info else None
    if not currency:
        info = ticker_obj.info
        currency = info.get("currency") if isinstance(info, dict) else None
    return {
        "ticker": ticker,
        "price": latest_price,
        "price_as_of": latest_date,
        "currency": currency or "USD",
        "source": "Yahoo Finance via yfinance",
    }


def _ticker_market(ticker: str) -> str:
    upper = str(ticker or "").strip().upper()
    if upper.endswith(".HK"):
        return "HK"
    if upper.endswith(".SH") or upper.endswith(".SZ") or upper.endswith(".SS"):
        return "CN"
    if re.fullmatch(r"\d{6}", upper):
        return "CN"
    return "US"


def _ticker_to_futu_code(ticker: str) -> str | None:
    upper = str(ticker or "").strip().upper()
    if not upper:
        return None
    if upper.endswith(".HK"):
        raw = upper.replace(".HK", "")
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            return f"HK.{digits.zfill(5)}"
        return None
    if upper.endswith(".SH"):
        return f"SH.{upper.replace('.SH', '')}"
    if upper.endswith(".SS"):
        return f"SH.{upper.replace('.SS', '')}"
    if upper.endswith(".SZ"):
        return f"SZ.{upper.replace('.SZ', '')}"
    if re.fullmatch(r"\d{6}", upper):
        if upper.startswith("6"):
            return f"SH.{upper}"
        return f"SZ.{upper}"
    if re.fullmatch(r"[A-Z][A-Z0-9.-]*", upper):
        us_symbol = upper.replace("-", ".")
        return f"US.{us_symbol}"
    return None


def _should_prefer_futu_for_ticker(ticker: str, futu_runtime: Dict[str, Any] | None) -> bool:
    if not futu_runtime or str(futu_runtime.get("status") or "") != "verified":
        return False
    market = _ticker_market(ticker)
    permissions = futu_runtime.get("market_permissions") or {}
    return str(permissions.get(market) or "") == "ok"


def _fetch_quote_from_futu(
    ticker: str,
    ctx: Any,
    futu_runtime: Dict[str, Any],
) -> Dict[str, Any] | None:
    if RET_OK is None:
        return None
    if not _should_prefer_futu_for_ticker(ticker, futu_runtime):
        return None
    futu_code = _ticker_to_futu_code(ticker)
    if not futu_code:
        return None
    try:
        ret, data = ctx.get_market_snapshot([futu_code])
    except Exception:  # noqa: BLE001
        return None
    if ret != RET_OK or data is None or data.empty:
        return None
    row = data.iloc[0]
    try:
        price = float(row.get("last_price"))
    except Exception:  # noqa: BLE001
        return None
    update_time = str(row.get("update_time") or "")
    if len(update_time) >= 10:
        price_as_of = update_time[:10]
    else:
        price_as_of = datetime.now(timezone.utc).date().isoformat()
    market = _ticker_market(ticker)
    currency = {"HK": "HKD", "CN": "CNY", "US": "USD"}.get(market, "USD")
    return {
        "ticker": ticker,
        "price": price,
        "price_as_of": price_as_of,
        "currency": currency,
        "source": "Futu OpenD",
    }


def infer_ticker_from_asset(asset: str) -> str | None:
    lowered = asset.lower()
    for keyword, ticker in ASSET_TICKER_HINTS.items():
        if keyword in lowered:
            return ticker
    return None


def infer_asset_cn(asset: str, ticker: str | None) -> str | None:
    if ticker:
        normalized = ticker.upper()
        if normalized in TICKER_NAME_CN:
            return TICKER_NAME_CN[normalized]

    lowered = asset.lower()
    for code, name_cn in TICKER_NAME_CN.items():
        english_hint = code.lower()
        pattern = rf"(^|[^a-z0-9]){re.escape(english_hint)}([^a-z0-9]|$)"
        if re.search(pattern, lowered):
            return name_cn
    if "apple" in lowered:
        return "苹果"
    if "amazon" in lowered:
        return "亚马逊"
    if "microsoft" in lowered:
        return "微软"
    if "nvidia" in lowered:
        return "英伟达"
    if "tesla" in lowered:
        return "特斯拉"
    if "alibaba" in lowered:
        return "阿里巴巴"
    if "berkshire" in lowered:
        return "伯克希尔·哈撒韦"
    if "tencent" in lowered:
        return "腾讯"
    if "pdd" in lowered:
        return "拼多多"
    return None


def _wiki_get_json(url: str) -> Dict[str, Any] | None:
    request = urllib.request.Request(url, headers={"User-Agent": WIKI_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def fetch_wikipedia_avatar(title: str, lang: str = "en") -> str | None:
    encoded = urllib.parse.quote(title, safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    payload = _wiki_get_json(url)
    if not payload:
        return None
    thumb = payload.get("thumbnail")
    if isinstance(thumb, dict):
        src = thumb.get("source")
        if isinstance(src, str) and src.startswith("http"):
            return src
    original = payload.get("originalimage")
    if isinstance(original, dict):
        src = original.get("source")
        if isinstance(src, str) and src.startswith("http"):
            return src
    return None


def build_avatar_map(investors: List[Dict[str, Any]]) -> Dict[str, str]:
    avatar_map: Dict[str, str] = {}
    for item in investors:
        investor_id = str(item.get("id") or "")
        override = INVESTOR_AVATAR_OVERRIDES.get(investor_id)
        if override:
            avatar_map[investor_id] = override
            continue
        title = INVESTOR_WIKI_TITLES.get(investor_id) or str(item.get("name_en") or "")
        avatar = None
        if title:
            avatar = fetch_wikipedia_avatar(title, lang="en")
        if not avatar:
            name_cn = str(item.get("name_cn") or "")
            if name_cn:
                avatar = fetch_wikipedia_avatar(name_cn, lang="zh")
        if avatar:
            avatar_map[investor_id] = avatar
    return avatar_map


def _http_get_text(url: str, user_agent: str, retries: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as error:  # noqa: BLE001
            last_error = error
            time.sleep(0.5 * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError(f"failed to fetch: {url}")


def _http_get_json(url: str, user_agent: str, retries: int = 3) -> Dict[str, Any]:
    return json.loads(_http_get_text(url, user_agent=user_agent, retries=retries))


def _sec_get_json(url: str) -> Dict[str, Any]:
    return _http_get_json(url, user_agent=SEC_USER_AGENT, retries=4)


def _sec_get_text(url: str) -> str:
    return _http_get_text(url, user_agent=SEC_USER_AGENT, retries=4)


def _normalize_xml_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _extract_13f_holdings_map(xml_text: str) -> Dict[str, float]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    issuer_value: Dict[str, float] = {}
    for info_table in root.iter():
        if _normalize_xml_tag(info_table.tag) != "infoTable":
            continue
        issuer = ""
        value_text = ""
        for child in info_table:
            tag = _normalize_xml_tag(child.tag)
            if tag == "nameOfIssuer":
                issuer = (child.text or "").strip().upper()
            elif tag == "value":
                value_text = (child.text or "").strip()
        if not issuer or not value_text:
            continue
        try:
            value = float(value_text)
        except ValueError:
            continue
        issuer_value[issuer] = issuer_value.get(issuer, 0.0) + value
    return issuer_value


def _find_recent_13f(cik: str, limit: int = 2) -> List[Tuple[str, str]]:
    data = _sec_get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    report_dates = recent.get("reportDate", [])
    result: List[Tuple[str, str]] = []
    for form, accession, report_date in zip(forms, accessions, report_dates):
        if form == "13F-HR":
            result.append((accession, report_date))
        if len(result) >= limit:
            break
    return result


def _fetch_13f_snapshot(cik: str, accession: str, report_date: str) -> Dict[str, Any] | None:
    accession_no_dash = accession.replace("-", "")
    cik_numeric = str(int(cik))
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession_no_dash}/index.json"
    index_payload = _sec_get_json(index_url)
    items = index_payload.get("directory", {}).get("item", [])
    xml_name = None
    for item in items:
        name = str(item.get("name", ""))
        if name.lower().endswith(".xml") and "info" in name.lower():
            xml_name = name
            break
    if xml_name is None:
        for item in items:
            name = str(item.get("name", ""))
            if name.lower().endswith(".xml") and name != "primary_doc.xml":
                xml_name = name
                break
    if not xml_name:
        return None

    xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession_no_dash}/{xml_name}"
    xml_text = _sec_get_text(xml_url)
    issuer_value = _extract_13f_holdings_map(xml_text)
    total_value = sum(issuer_value.values())
    if total_value <= 0:
        return None
    return {
        "accession": accession,
        "report_date": report_date,
        "issuer_value": issuer_value,
        "total_value": total_value,
        "source": "SEC EDGAR",
    }


def _strip_html(raw_html: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", raw_html)
    return " ".join(unescape(no_tags).split())


def _parse_quarter_to_report_date(quarter_text: str) -> str | None:
    match = re.match(r"Q([1-4])\s+(\d{4})", quarter_text.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    quarter = int(match.group(1))
    year = int(match.group(2))
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    return f"{year}-{month_day}"


def _parse_kusd_text(value_kusd_text: str) -> float | None:
    cleaned = re.sub(r"[^\d.\-]", "", str(value_kusd_text or ""))
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def _is_valid_13f_form_type(form_type: str) -> bool:
    upper = str(form_type or "").strip().upper()
    if not upper:
        return True
    if "NOTICE" in upper:
        return False
    return upper.startswith("13F-HR") or "RESTATEMENT" in upper


def _fetch_13f_info_manager_rows(cik: str, limit: int = 2) -> List[Dict[str, str]]:
    manager_url = f"{THIRTEENF_INFO_BASE}/manager/{cik}"
    html_text = _http_get_text(manager_url, user_agent=THIRTEENF_INFO_USER_AGENT, retries=3)
    table_match = re.search(
        r'<table id="managerFilings".*?<tbody[^>]*>(.*?)</tbody>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not table_match:
        return []

    rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", table_match.group(1), flags=re.IGNORECASE | re.DOTALL)
    rows: List[Dict[str, str]] = []
    for row_html in rows_html:
        cols = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)
        if len(cols) < 7:
            continue
        detail_href_match = re.search(r'href="([^"]+)"', cols[0], flags=re.IGNORECASE)
        quarter_text = _strip_html(cols[0])
        rows.append(
            {
                "quarter": quarter_text,
                "detail_href": detail_href_match.group(1) if detail_href_match else "",
                "holdings_count": _strip_html(cols[1]),
                "value_kusd_text": _strip_html(cols[2]),
                "top_holdings_text": _strip_html(cols[3]),
                "form_type": _strip_html(cols[4]),
                "date_filed": _strip_html(cols[5]),
                "filing_id": _strip_html(cols[6]),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _build_13f_value_series_from_manager_rows(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    seen_report_dates: set[str] = set()
    series: List[Dict[str, Any]] = []
    for row in rows:
        form_type = str(row.get("form_type") or "")
        if not _is_valid_13f_form_type(form_type):
            continue
        report_date = _parse_quarter_to_report_date(str(row.get("quarter") or ""))
        if not report_date or report_date in seen_report_dates:
            continue
        value_kusd = _parse_kusd_text(str(row.get("value_kusd_text") or ""))
        if value_kusd is None:
            continue
        seen_report_dates.add(report_date)
        series.append(
            {
                "report_date": report_date,
                "value_kusd": value_kusd,
                "quarter": str(row.get("quarter") or ""),
                "date_filed": str(row.get("date_filed") or ""),
                "form_type": form_type,
                "filing_id": str(row.get("filing_id") or ""),
            }
        )
    series.sort(key=lambda item: str(item.get("report_date") or ""))
    return series


def _compute_13f_value_cagr_proxy(series: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if len(series) < 2:
        return None
    start = series[0]
    end = series[-1]
    try:
        start_value = float(start["value_kusd"])
        end_value = float(end["value_kusd"])
        start_dt = datetime.fromisoformat(str(start["report_date"]))
        end_dt = datetime.fromisoformat(str(end["report_date"]))
    except Exception:  # noqa: BLE001
        return None
    if start_value <= 0 or end_value <= 0:
        return None
    day_span = (end_dt - start_dt).days
    if day_span < 365:
        return None
    years = day_span / 365.25
    try:
        cagr = (end_value / start_value) ** (1.0 / years) - 1.0
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(cagr, float):
        return None
    return {
        "annualized_return_proxy_pct": round(cagr * 100.0, 2),
        "annualized_return_proxy_period": f"{start['report_date']} - {end['report_date']}",
        "annualized_return_proxy_basis": "13F价值序列CAGR代理（非审计净值，含资金流影响）",
        "annualized_return_proxy_note": (
            "该值由披露实体13F组合“市值”序列计算，不代表基金审计净值年化；"
            "会受申购赎回、资金划转、口径差异影响，仅可作粗粒度参考。"
        ),
        "annualized_return_proxy_start_value_kusd": round(start_value, 2),
        "annualized_return_proxy_end_value_kusd": round(end_value, 2),
        "annualized_return_proxy_points": len(series),
        "annualized_return_proxy_latest_report_date": str(end["report_date"]),
    }


def build_13f_proxy_return_context(investors: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    context: Dict[str, Dict[str, Any]] = {}
    for item in investors:
        investor_id = str(item.get("id") or "")
        role_type = str(item.get("role_type") or "investor")
        if role_type in {"insider", "politician_disclosure", "public_figure"}:
            continue
        if isinstance(item.get("calibrated_return_pct"), (int, float)):
            continue
        cik = SEC_CIK_BY_INVESTOR.get(investor_id)
        if not cik:
            continue
        try:
            manager_rows = _fetch_13f_info_manager_rows(cik, limit=120)
            series = _build_13f_value_series_from_manager_rows(manager_rows)
            proxy = _compute_13f_value_cagr_proxy(series)
            if not proxy:
                continue
            context[investor_id] = {
                **proxy,
                "annualized_return_proxy_source": "13f.info manager filings table (SEC 13F mirror)",
            }
        except Exception:  # noqa: BLE001
            continue
    return context


def _probe_futu_market_permission(ctx: Any, code: str) -> Dict[str, str]:
    if RET_OK is None:
        return {"status": "unavailable", "note": "futu sdk not available"}
    try:
        ret, data = ctx.get_market_snapshot([code])
    except Exception as error:  # noqa: BLE001
        return {"status": "error", "note": str(error)[:200]}
    if ret == RET_OK and data is not None and not data.empty:
        return {"status": "ok", "note": "quote success"}
    message = str(data)[:240]
    if "无权限" in message or "权限" in message:
        return {"status": "no_permission", "note": message}
    return {"status": "error", "note": message}


def detect_futu_opend_status(host: str = "127.0.0.1", ports: Tuple[int, int] = FUTU_OPEND_PORTS) -> Dict[str, Any]:
    if OpenQuoteContext is None:
        return {
            "status": "unavailable",
            "endpoint": None,
            "port": None,
            "note": "futu sdk 未安装，无法检测 OpenD。",
            "market_permissions": {"US": "unavailable", "HK": "unavailable", "CN": "unavailable"},
        }

    open_port: int | None = None
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1.0)
            if sock.connect_ex((host, port)) == 0:
                open_port = port
                break
        finally:
            sock.close()

    if open_port is None:
        return {
            "status": "unreachable",
            "endpoint": f"{host}:{ports[0]} or {host}:{ports[1]}",
            "port": None,
            "note": "OpenD 连接失败（ECONNREFUSED），当前无法自动对照富途持仓页。",
            "market_permissions": {"US": "unreachable", "HK": "unreachable", "CN": "unreachable"},
        }

    ctx = None
    try:
        ctx = OpenQuoteContext(host=host, port=open_port)
        us = _probe_futu_market_permission(ctx, "US.AAPL")
        hk = _probe_futu_market_permission(ctx, "HK.00700")
        cn = _probe_futu_market_permission(ctx, "SH.600519")
        market_permissions = {"US": us["status"], "HK": hk["status"], "CN": cn["status"]}
        if any(item["status"] == "ok" for item in (us, hk, cn)):
            status = "verified"
            note = "OpenD 可用，已完成行情权限探测。"
        elif all(item["status"] == "no_permission" for item in (us, hk, cn)):
            status = "connected_but_no_permission"
            note = "OpenD 已连接，但三个市场均无行情权限。"
        else:
            status = "port_open_unverified"
            note = "OpenD 端口可连通，但权限/握手异常，需人工复核。"
        return {
            "status": status,
            "endpoint": f"{host}:{open_port}",
            "port": open_port,
            "note": note,
            "market_permissions": market_permissions,
            "market_probe_note": {
                "US": us["note"],
                "HK": hk["note"],
                "CN": cn["note"],
            },
        }
    except Exception as error:  # noqa: BLE001
        return {
            "status": "port_open_unverified",
            "endpoint": f"{host}:{open_port}",
            "port": open_port,
            "note": f"OpenD 端口可连通，但API调用异常：{str(error)[:200]}",
            "market_permissions": {"US": "error", "HK": "error", "CN": "error"},
        }
    finally:
        try:
            if ctx is not None:
                ctx.close()
        except Exception:  # noqa: BLE001
            pass


def _normalize_13f_symbol(symbol: str, issuer: str) -> str:
    raw = (symbol or "").strip().upper()
    if raw in THIRTEENF_TICKER_NORMALIZATION:
        return THIRTEENF_TICKER_NORMALIZATION[raw]
    if raw:
        return raw
    issuer_upper = (issuer or "").upper()
    for ticker, keywords in SEC_ISSUER_KEYWORDS_BY_TICKER.items():
        if any(keyword in issuer_upper for keyword in keywords):
            return ticker
    return ""


def _fetch_13f_info_snapshot(filing_row: Dict[str, str]) -> Dict[str, Any] | None:
    filing_id = str(filing_row.get("filing_id") or "").strip()
    if not filing_id:
        return None

    payload = _http_get_json(
        f"{THIRTEENF_INFO_BASE}/data/13f/{filing_id}",
        user_agent=THIRTEENF_INFO_USER_AGENT,
        retries=3,
    )
    rows = payload.get("data", [])
    if not isinstance(rows, list) or not rows:
        return None

    issuer_value: Dict[str, float] = {}
    detailed_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            continue
        symbol = str(row[0] or "").strip()
        issuer = str(row[1] or "").strip()
        value = row[4]
        weight_pct = row[5]
        try:
            value_num = float(value)
        except (TypeError, ValueError):
            continue

        issuer_upper = issuer.upper()
        issuer_value[issuer_upper] = issuer_value.get(issuer_upper, 0.0) + value_num

        ticker = _normalize_13f_symbol(symbol, issuer)
        try:
            weight_pct_num = float(weight_pct)
        except (TypeError, ValueError):
            weight_pct_num = None

        detailed_rows.append(
            {
                "ticker": ticker,
                "issuer": issuer,
                "value_kusd": value_num,
                "weight_pct": weight_pct_num,
            }
        )

    total_value = sum(issuer_value.values())
    if total_value <= 0:
        return None

    return {
        "accession": filing_id,
        "report_date": _parse_quarter_to_report_date(str(filing_row.get("quarter") or "")) or str(
            filing_row.get("quarter") or "未知"
        ),
        "issuer_value": issuer_value,
        "total_value": total_value,
        "source": "13f.info mirror (SEC 13F)",
        "form_type": str(filing_row.get("form_type") or ""),
        "date_filed": str(filing_row.get("date_filed") or ""),
        "holdings_detailed": detailed_rows,
        "detail_url": (
            f"{THIRTEENF_INFO_BASE}{filing_row.get('detail_href')}"
            if str(filing_row.get("detail_href") or "").startswith("/")
            else str(filing_row.get("detail_href") or "")
        ),
    }


def build_13f_change_context(investors: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    context: Dict[str, Dict[str, Any]] = {}
    for item in investors:
        investor_id = str(item.get("id") or "")
        cik = SEC_CIK_BY_INVESTOR.get(investor_id)
        if not cik:
            continue

        current: Dict[str, Any] | None = None
        previous: Dict[str, Any] | None = None

        try:
            filings = _find_recent_13f(cik, limit=2)
            if filings:
                current = _fetch_13f_snapshot(cik, filings[0][0], filings[0][1])
                previous = _fetch_13f_snapshot(cik, filings[1][0], filings[1][1]) if len(filings) > 1 else None
        except Exception:  # noqa: BLE001
            current = None
            previous = None

        # SEC 官方接口偶发 503 时，回退到 13f.info 镜像（数据仍来源 SEC 13F）。
        if current is None:
            try:
                manager_rows = _fetch_13f_info_manager_rows(cik, limit=3)
                snapshots: List[Dict[str, Any]] = []
                for row in manager_rows:
                    snap = _fetch_13f_info_snapshot(row)
                    if snap:
                        snapshots.append(snap)
                    if len(snapshots) >= 2:
                        break
                if snapshots:
                    current = snapshots[0]
                    previous = snapshots[1] if len(snapshots) > 1 else None
            except Exception:  # noqa: BLE001
                current = None
                previous = None

        if current is None:
            continue

        context[investor_id] = {
            "current": current,
            "previous": previous,
        }
    return context


def get_quote_map(
    tickers: List[str],
    cache_dir: Path,
    ttl_hours: int,
    use_cache: bool,
    futu_runtime: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Dict[str, Any]], int, int]:
    result: Dict[str, Dict[str, Any]] = {}
    cache_hits = 0
    api_fetches = 0

    futu_ctx = None
    if futu_runtime and str(futu_runtime.get("status") or "") == "verified" and OpenQuoteContext is not None:
        port = futu_runtime.get("port")
        if isinstance(port, int):
            try:
                futu_ctx = OpenQuoteContext(host="127.0.0.1", port=port)
            except Exception:  # noqa: BLE001
                futu_ctx = None

    try:
        for ticker in sorted(set(ticker.strip().upper() for ticker in tickers if ticker)):
            prefer_futu = _should_prefer_futu_for_ticker(ticker, futu_runtime)
            cache_file = _cache_path(cache_dir, ticker)
            if use_cache:
                cached = _load_cached_quote(cache_file, ttl_hours=ttl_hours)
                if cached is not None:
                    cached_source = str(cached.get("source") or "")
                    if not (prefer_futu and "Futu OpenD" not in cached_source):
                        result[ticker] = cached
                        cache_hits += 1
                        continue

            quote = None
            if futu_ctx is not None and prefer_futu:
                quote = _fetch_quote_from_futu(ticker, ctx=futu_ctx, futu_runtime=futu_runtime or {})
            if quote is None:
                quote = fetch_quote(ticker)
            if quote is None:
                continue
            result[ticker] = quote
            api_fetches += 1
            if use_cache:
                _save_cached_quote(cache_file, quote)
    finally:
        try:
            if futu_ctx is not None:
                futu_ctx.close()
        except Exception:  # noqa: BLE001
            pass
    return result, cache_hits, api_fetches


def build_intro(item: Dict[str, Any]) -> str:
    investor_id = str(item.get("id", ""))
    if investor_id in PERSONAL_INTRO_OVERRIDES:
        return PERSONAL_INTRO_OVERRIDES[investor_id]
    if item.get("personal_intro"):
        return str(item.get("personal_intro"))

    name_cn = str(item.get("name_cn") or item.get("name_en") or "该投资者")
    style = str(item.get("style") or "多策略")
    thesis = str(item.get("thesis") or "公开资料研究")
    return DEFAULT_INTRO_TEMPLATE.format(name_cn=name_cn, style=style, thesis=thesis)


def build_performance_summary(item: Dict[str, Any]) -> str:
    pct = item.get("calibrated_return_pct")
    period = str(item.get("period") or "未知区间")
    basis = str(item.get("return_basis") or "未披露口径")
    if isinstance(pct, (int, float)):
        return f"公开口径年化约 {pct}%（区间：{period}；口径：{basis}）"
    proxy_pct = item.get("annualized_return_proxy_pct")
    proxy_period = str(item.get("annualized_return_proxy_period") or "未知")
    proxy_basis = str(item.get("annualized_return_proxy_basis") or "")
    if isinstance(proxy_pct, (int, float)):
        return (
            f"暂无统一可审计长期年化收益率；13F代理年化约 {proxy_pct}% "
            f"（区间：{proxy_period}；口径：{proxy_basis}）"
        )
    return f"暂无统一可审计长期年化收益率（区间：{period}；口径：{basis}）"


def normalize_holdings(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    weighted = item.get("representative_holdings_with_weight")
    if isinstance(weighted, list) and weighted:
        return [dict(row) for row in weighted]
    base_holdings = item.get("representative_holdings") or []
    rows: List[Dict[str, Any]] = []
    for asset in base_holdings:
        rows.append(
            {
                "asset": asset,
                "ticker": None,
                "weight_pct": None,
                "weight_text": "未披露/不适用",
                "weight_note": "公开资料无统一可审计组合占比",
                "weight_as_of": None,
            }
        )
    return rows


def _calc_13f_weight(ticker: str, snapshot: Dict[str, Any]) -> float | None:
    detailed = snapshot.get("holdings_detailed")
    if isinstance(detailed, list):
        matched_weight_pct = 0.0
        matched = False
        for row in detailed:
            if not isinstance(row, dict):
                continue
            if str(row.get("ticker") or "").strip().upper() != ticker:
                continue
            matched = True
            weight_pct = row.get("weight_pct")
            try:
                if weight_pct is not None:
                    matched_weight_pct += float(weight_pct)
                    continue
            except (TypeError, ValueError):
                pass
            try:
                value_kusd = float(row.get("value_kusd") or 0.0)
                total = float(snapshot.get("total_value", 0.0))
                if total > 0:
                    matched_weight_pct += value_kusd / total * 100.0
            except (TypeError, ValueError):
                continue
        if matched and matched_weight_pct > 0:
            return matched_weight_pct

    keywords = SEC_ISSUER_KEYWORDS_BY_TICKER.get(ticker, [])
    if not keywords:
        return None
    issuer_value = snapshot.get("issuer_value", {})
    total = float(snapshot.get("total_value", 0.0))
    if total <= 0:
        return None
    matched = 0.0
    for issuer, value in issuer_value.items():
        if any(keyword in issuer for keyword in keywords):
            matched += float(value)
    if matched <= 0:
        return None
    return matched / total * 100.0


def _build_holdings_from_13f_snapshot(snapshot: Dict[str, Any], limit: int = 8) -> List[Dict[str, Any]]:
    detailed = snapshot.get("holdings_detailed")
    rows: List[Dict[str, Any]] = []
    if isinstance(detailed, list) and detailed:
        sorted_rows = sorted(
            [row for row in detailed if isinstance(row, dict)],
            key=lambda row: float(row.get("value_kusd") or 0.0),
            reverse=True,
        )
        for row in sorted_rows[:limit]:
            issuer = str(row.get("issuer") or "").strip()
            ticker = str(row.get("ticker") or "").strip().upper()
            weight_pct = row.get("weight_pct")
            try:
                weight_pct_num = float(weight_pct) if weight_pct is not None else None
            except (TypeError, ValueError):
                weight_pct_num = None
            rows.append(
                {
                    "asset": issuer or (ticker or "未知资产"),
                    "ticker": ticker or None,
                    "weight_pct": round(weight_pct_num, 2) if weight_pct_num is not None else None,
                    "weight_text": f"{weight_pct_num:.2f}%"
                    if weight_pct_num is not None
                    else "未披露/不适用",
                    "weight_note": "可核验：13F披露实体最新报告（US长仓口径）",
                    "weight_as_of": snapshot.get("report_date"),
                    "weight_source": snapshot.get("accession"),
                    "weight_basis": snapshot.get("source") or "SEC 13F",
                }
            )
        return rows

    issuer_value = snapshot.get("issuer_value", {})
    total = float(snapshot.get("total_value", 0.0))
    if not isinstance(issuer_value, dict) or total <= 0:
        return []
    sorted_rows = sorted(issuer_value.items(), key=lambda x: float(x[1]), reverse=True)
    for issuer, value in sorted_rows[:limit]:
        issuer_text = str(issuer).strip()
        try:
            value_num = float(value)
        except (TypeError, ValueError):
            continue
        inferred_ticker = ""
        issuer_upper = issuer_text.upper()
        for ticker, keywords in SEC_ISSUER_KEYWORDS_BY_TICKER.items():
            if any(keyword in issuer_upper for keyword in keywords):
                inferred_ticker = ticker
                break
        weight_pct_num = value_num / total * 100.0
        rows.append(
            {
                "asset": issuer_text or "未知资产",
                "ticker": inferred_ticker or None,
                "weight_pct": round(weight_pct_num, 2),
                "weight_text": f"{weight_pct_num:.2f}%",
                "weight_note": "可核验：13F披露实体最新报告（US长仓口径）",
                "weight_as_of": snapshot.get("report_date"),
                "weight_source": snapshot.get("accession"),
                "weight_basis": snapshot.get("source") or "SEC 13F",
            }
        )
    return rows


def enrich_holding_row(
    row: Dict[str, Any],
    quote_map: Dict[str, Dict[str, Any]],
    investor_id: str,
    change_context: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    enriched = dict(row)
    inference_asset = str(enriched.get("asset_for_inference") or enriched.get("asset") or "")

    ticker = str(enriched.get("ticker") or "").strip().upper()
    if not ticker:
        inferred = infer_ticker_from_asset(inference_asset)
        ticker = inferred.upper() if inferred else ""
        if ticker:
            enriched["ticker"] = ticker
    asset_cn = enriched.get("asset_cn")
    if not asset_cn:
        inferred_cn = infer_asset_cn(inference_asset, ticker if ticker else None)
        if inferred_cn:
            enriched["asset_cn"] = inferred_cn
        else:
            enriched["asset_cn"] = str(enriched.get("asset") or "")

    if ticker:
        quote = quote_map.get(ticker)
        if quote:
            price = float(quote["price"])
            enriched["price"] = round(price, 4)
            enriched["price_text"] = f"{price:.4f}"
            enriched["price_currency"] = quote.get("currency", "USD")
            enriched["price_as_of"] = quote.get("price_as_of")
            enriched["price_source"] = quote.get("source")
        else:
            enriched["price"] = None
            enriched["price_text"] = "行情拉取失败"
            enriched["price_currency"] = None
            enriched["price_as_of"] = None
            enriched["price_source"] = None
    else:
        enriched["price"] = None
        enriched["price_text"] = "不适用（非标准股票代码）"
        enriched["price_currency"] = None
        enriched["price_as_of"] = None
        enriched["price_source"] = None

    weight_text = str(enriched.get("weight_text") or "未披露/不适用")
    weight_as_of = enriched.get("weight_as_of")
    enriched["weight_text"] = weight_text
    enriched["weight_as_of"] = weight_as_of or "未披露/不适用"
    enriched["holding_updated_at"] = weight_as_of or "未披露/不适用"

    if "position_change_pct" not in enriched:
        enriched["position_change_pct"] = None
    if "position_change_text" not in enriched:
        enriched["position_change_text"] = "未披露/不适用"
    if "position_change_as_of" not in enriched:
        enriched["position_change_as_of"] = weight_as_of or "未披露/不适用"
    if "position_change_note" not in enriched:
        enriched["position_change_note"] = "缺少连续披露口径，暂无法计算仓位变动比例"
    if not enriched.get("position_change_as_of"):
        enriched["position_change_as_of"] = "未披露/不适用"

    # 尝试用 13F 回填当前权重 + 计算连续两期仓位变动。
    investor_ctx = change_context.get(investor_id, {})
    current_snapshot = investor_ctx.get("current")
    previous_snapshot = investor_ctx.get("previous")
    current_weight = _calc_13f_weight(ticker, current_snapshot) if ticker and current_snapshot else None
    if current_weight is not None:
        if enriched.get("weight_pct") in (None, "") and ("未披露" in weight_text or weight_text == "-"):
            enriched["weight_pct"] = round(current_weight, 2)
            enriched["weight_text"] = f"{current_weight:.2f}%"
            enriched["weight_note"] = "可核验：13F披露实体最新报告（US长仓口径）"
            enriched["weight_as_of"] = current_snapshot.get("report_date") or "未披露/不适用"
            enriched["holding_updated_at"] = current_snapshot.get("report_date") or "未披露/不适用"
            source = current_snapshot.get("source") or "SEC 13F"
            accession = current_snapshot.get("accession")
            enriched["weight_source"] = f"{source} {accession}" if accession else source

    if ticker and current_snapshot and previous_snapshot:
        previous_weight = _calc_13f_weight(ticker, previous_snapshot)
        if current_weight is not None and previous_weight is not None:
            delta_pp = current_weight - previous_weight
            enriched["position_change_pct"] = round(delta_pp, 2)
            enriched["position_change_text"] = f"{delta_pp:+.2f}pp"
            enriched["position_change_as_of"] = current_snapshot.get("report_date")
            enriched["position_change_note"] = (
                f"对比上期13F（{previous_snapshot.get('report_date')} -> {current_snapshot.get('report_date')}）"
            )
        elif current_weight is not None and previous_weight is None:
            enriched["position_change_text"] = "新增/上期未披露"
            enriched["position_change_as_of"] = current_snapshot.get("report_date")
            enriched["position_change_note"] = "当前13F命中，上期13F未命中"

    enriched.pop("asset_for_inference", None)
    return enriched


def _build_futu_alignment_fields(
    investor_id: str,
    role_type: str,
    has_13f_snapshot: bool,
    futu_runtime: Dict[str, str],
) -> Dict[str, str]:
    runtime_status = str(futu_runtime.get("status") or "unknown")
    runtime_note = str(futu_runtime.get("note") or "")
    if role_type in {"politician_disclosure", "public_figure"}:
        return {
            "futu_alignment_status": "not_applicable_complete_portfolio",
            "futu_alignment_note": "该主体主要为交易事件披露，通常不具备可比的完整组合口径。",
        }
    if role_type == "insider":
        if investor_id in HYBRID_LOOKTHROUGH_13F_BY_INVESTOR and has_13f_snapshot:
            return {
                "futu_alignment_status": "partial_direct_plus_lookthrough",
                "futu_alignment_note": (
                    "已采用“管理层直接持股+公司13F间接敞口”双层口径；"
                    "非个人完整账户。"
                ),
            }
        return {
            "futu_alignment_status": "insider_disclosure_only",
            "futu_alignment_note": "该主体主要适用管理层持股披露，非标准13F基金组合口径。",
        }
    if has_13f_snapshot:
        if runtime_status == "verified":
            return {
                "futu_alignment_status": "ready_for_futu_compare",
                "futu_alignment_note": "已具备13F映射，可继续与富途页面做逐项对照。",
            }
        return {
            "futu_alignment_status": "pending_futu_runtime",
            "futu_alignment_note": f"已完成13F映射，但富途运行环境不可用：{runtime_note}",
        }
    return {
        "futu_alignment_status": "mapping_needed",
        "futu_alignment_note": "尚未建立稳定披露实体映射，暂无法进行富途逐项对照。",
    }


def _holding_dedupe_key(row: Dict[str, Any]) -> str:
    ticker = str(row.get("ticker") or "").strip().upper()
    if ticker:
        return f"ticker:{ticker}"
    asset = str(row.get("asset") or "").strip().upper()
    return f"asset:{asset}"


def normalize_investor(
    item: Dict[str, Any],
    quote_map: Dict[str, Dict[str, Any]],
    change_context: Dict[str, Dict[str, Any]],
    proxy_return_context: Dict[str, Dict[str, Any]],
    futu_runtime: Dict[str, str],
) -> Dict[str, Any]:
    normalized = dict(item)
    investor_id = str(normalized.get("id") or "")
    entity_meta = DISCLOSURE_ENTITY_BY_INVESTOR.get(investor_id)
    current_snapshot = (change_context.get(investor_id) or {}).get("current")
    role_type = str(normalized.get("role_type") or "investor")

    proxy = proxy_return_context.get(investor_id)
    if proxy and not isinstance(normalized.get("calibrated_return_pct"), (int, float)):
        normalized.update(proxy)
        normalized["return_basis"] = normalized.get("return_basis") or "not_publicly_audited"
        normalized["period"] = normalized.get("period") or str(proxy.get("annualized_return_proxy_period") or "未知")
        normalized["source_refs"] = list(
            dict.fromkeys(list(normalized.get("source_refs") or []) + ["13f_value_cagr_proxy"])
        )

    if entity_meta:
        normalized["disclosure_entity"] = {
            "entity_name": entity_meta.get("entity_name"),
            "cik": entity_meta.get("cik"),
            "source": current_snapshot.get("source") if isinstance(current_snapshot, dict) else None,
            "report_date": current_snapshot.get("report_date") if isinstance(current_snapshot, dict) else None,
            "accession": current_snapshot.get("accession") if isinstance(current_snapshot, dict) else None,
            "form_type": current_snapshot.get("form_type") if isinstance(current_snapshot, dict) else None,
            "date_filed": current_snapshot.get("date_filed") if isinstance(current_snapshot, dict) else None,
            "detail_url": current_snapshot.get("detail_url") if isinstance(current_snapshot, dict) else None,
            "status": "ok" if current_snapshot else "not_found",
        }
    else:
        if role_type == "politician_disclosure":
            normalized["disclosure_entity"] = {
                "entity_name": "美国国会议员交易公开披露",
                "cik": None,
                "source": "Congressional disclosure trackers",
                "report_date": None,
                "accession": None,
                "form_type": None,
                "date_filed": None,
                "detail_url": None,
                "status": "not_applicable_13f",
            }
        elif role_type == "insider":
            normalized["disclosure_entity"] = {
                "entity_name": "SEC Insider Filings",
                "cik": None,
                "source": "SEC insider disclosures",
                "report_date": None,
                "accession": None,
                "form_type": None,
                "date_filed": None,
                "detail_url": None,
                "status": "insider_disclosure",
            }
        else:
            normalized["disclosure_entity"] = None

    normalized["role_type"] = role_type
    normalized["personal_intro"] = build_intro(item)
    normalized["performance_summary"] = str(item.get("performance_summary") or build_performance_summary(normalized))
    normalized["methodology_bucket"] = normalized.get("methodology_bucket", normalized.get("style", "未分类"))

    holdings = normalize_holdings(item)

    if investor_id in HYBRID_LOOKTHROUGH_13F_BY_INVESTOR:
        lookthrough_rows: List[Dict[str, Any]] = []
        if current_snapshot:
            for row in _build_holdings_from_13f_snapshot(
                current_snapshot, limit=HYBRID_LOOKTHROUGH_13F_BY_INVESTOR[investor_id]
            ):
                indirect = dict(row)
                indirect_asset = str(indirect.get("asset") or indirect.get("ticker") or "未知资产")
                indirect["asset"] = f"（间接，NVIDIA 13F）{indirect_asset}"
                indirect["asset_for_inference"] = indirect_asset
                indirect["holding_layer"] = "indirect_13f_lookthrough"
                indirect["indirect_via_entity"] = "NVIDIA CORP"
                indirect["weight_note"] = (
                    "间接敞口：来自 NVIDIA 最新13F（美国长仓口径），"
                    "并非黄仁勋个人账户持仓。"
                )
                lookthrough_rows.append(indirect)
        if lookthrough_rows:
            holdings = holdings + lookthrough_rows
            normalized["holdings_note"] = (
                "双层口径：1) 黄仁勋个人直接持有 NVDA（管理层披露）；"
                "2) 英伟达公司13F间接敞口（美国长仓）。"
                "该口径用于观察“个人+公司资本配置”，不等同于个人完整投资组合。"
            )
            normalized["source_refs"] = list(
                dict.fromkeys(
                    list(normalized.get("source_refs") or [])
                    + ["sec_insider_filings", "sec_13f_disclosure_entity", "13f_info_mirror"]
                )
            )

    if investor_id in AUTO_POPULATE_HOLDINGS_FROM_13F:
        original_holdings = holdings
        auto_rows = (
            _build_holdings_from_13f_snapshot(
                current_snapshot, limit=AUTO_POPULATE_HOLDINGS_FROM_13F[investor_id]
            )
            if current_snapshot
            else []
        )
        if auto_rows:
            auto_keys = {_holding_dedupe_key(row) for row in auto_rows}
            supplemental_rows = [
                row for row in original_holdings if _holding_dedupe_key(row) not in auto_keys
            ]
            holdings = auto_rows + supplemental_rows
            entity = DISCLOSURE_ENTITY_BY_INVESTOR.get(investor_id, {})
            entity_name = entity.get("entity_name", "关联披露实体")
            cik = entity.get("cik", "")
            source = current_snapshot.get("source") if isinstance(current_snapshot, dict) else "SEC 13F"
            report_date = current_snapshot.get("report_date") if isinstance(current_snapshot, dict) else ""
            if supplemental_rows:
                normalized["holdings_note"] = (
                    f"已优先使用 {entity_name}（CIK {cik}）最新13F披露持仓；"
                    f"当前口径={source}，报告期={report_date}，仅覆盖美国长仓。"
                    f"同时补充了 {len(supplemental_rows)} 条非13F代表仓位（如港股/A股/历史代表仓位）。"
                )
            else:
                normalized["holdings_note"] = (
                    f"已优先使用 {entity_name}（CIK {cik}）最新13F披露持仓；"
                    f"当前口径={source}，报告期={report_date}，仅覆盖美国长仓，不包含非13F资产。"
                )
            normalized["source_refs"] = list(dict.fromkeys(
                list(normalized.get("source_refs") or [])
                + ["sec_13f_disclosure_entity", "13f_info_mirror"]
            ))

    normalized.update(
        _build_futu_alignment_fields(
            investor_id=investor_id,
            role_type=role_type,
            has_13f_snapshot=bool(current_snapshot),
            futu_runtime=futu_runtime,
        )
    )

    enriched_holdings = [
        enrich_holding_row(
            row,
            quote_map=quote_map,
            investor_id=investor_id,
            change_context=change_context,
        )
        for row in holdings
    ]
    normalized["representative_holdings_with_weight"] = enriched_holdings
    normalized["representative_holdings"] = [row.get("asset", "") for row in holdings]

    quote_eligible_rows = [row for row in enriched_holdings if str(row.get("ticker") or "").strip()]
    any_source_priced_rows = [row for row in quote_eligible_rows if str(row.get("price_source") or "").strip()]
    opend_rows = [row for row in enriched_holdings if str(row.get("price_source") or "") == "Futu OpenD"]
    known_weight_rows = [
        row
        for row in quote_eligible_rows
        if isinstance(row.get("weight_pct"), (int, float)) and float(row.get("weight_pct")) >= 0
    ]
    any_source_known_weight_rows = [
        row
        for row in any_source_priced_rows
        if isinstance(row.get("weight_pct"), (int, float)) and float(row.get("weight_pct")) >= 0
    ]
    opend_known_weight_rows = [
        row
        for row in opend_rows
        if isinstance(row.get("weight_pct"), (int, float)) and float(row.get("weight_pct")) >= 0
    ]
    known_weight_sum = sum(float(row.get("weight_pct") or 0.0) for row in known_weight_rows)
    any_source_weight_sum = sum(float(row.get("weight_pct") or 0.0) for row in any_source_known_weight_rows)
    opend_weight_sum = sum(float(row.get("weight_pct") or 0.0) for row in opend_known_weight_rows)

    normalized["interface_quant"] = {
        "eligible_asset_count": len(quote_eligible_rows),
        "priced_asset_count": len(any_source_priced_rows),
        "priced_asset_tickers": [str(row.get("ticker") or "") for row in any_source_priced_rows if row.get("ticker")],
        "priced_asset_coverage_pct": (
            round(len(any_source_priced_rows) / len(quote_eligible_rows) * 100.0, 2)
            if quote_eligible_rows
            else None
        ),
        "priced_weight_sum_pct": round(any_source_weight_sum, 2),
        "priced_weight_coverage_pct": (
            round(any_source_weight_sum / known_weight_sum * 100.0, 2) if known_weight_sum > 0 else None
        ),
        "missing_asset_count": max(len(quote_eligible_rows) - len(any_source_priced_rows), 0),
        "note": (
            "统计全部可用行情接口（Futu OpenD + Yahoo 等）对该投资者持仓的价格覆盖能力。"
            if any_source_priced_rows
            else "当前该投资者持仓暂无可用接口报价（或代码映射待完善）。"
        ),
    }
    normalized["opend_quant"] = {
        "priced_asset_count": len(opend_rows),
        "priced_asset_tickers": [str(row.get("ticker") or "") for row in opend_rows if row.get("ticker")],
        "priced_weight_sum_pct": round(opend_weight_sum, 2),
        "priced_weight_coverage_pct": (
            round(opend_weight_sum / known_weight_sum * 100.0, 2) if known_weight_sum > 0 else None
        ),
        "note": (
            "诊断指标：仅统计已命中 Futu OpenD 报价的持仓行；若组合权重未披露，则覆盖率不可计算。"
            if opend_rows
            else "诊断指标：当前该投资者持仓未命中 Futu OpenD 报价（或市场权限不足）。"
        ),
    }
    return normalized


def to_sort_key(item: Dict[str, Any]) -> Tuple[int, float, str]:
    role = str(item.get("role_type") or "")
    role_priority = {
        "investor": 0,
        "fund_manager": 1,
        "insider": 2,
        "politician_disclosure": 3,
        "public_figure": 4,
    }.get(role, 9)
    pct = item.get("calibrated_return_pct")
    proxy_pct = item.get("annualized_return_proxy_pct")
    if isinstance(pct, (int, float)):
        score = float(pct)
    elif isinstance(proxy_pct, (int, float)):
        score = float(proxy_pct)
    else:
        score = -9999.0
    return (role_priority, -score, str(item.get("name_cn") or item.get("name_en") or ""))


def main() -> None:
    args = parse_args()

    base_payload = load_json(args.base_file)
    additional_payload = load_json(args.additional_file)

    combined = [dict(item) for item in base_payload.get("investors", [])] + [
        dict(item) for item in additional_payload.get("investors", [])
    ]

    all_tickers: List[str] = []
    for item in combined:
        for row in normalize_holdings(item):
            ticker = row.get("ticker")
            if not ticker:
                ticker = infer_ticker_from_asset(str(row.get("asset") or ""))
            if ticker:
                all_tickers.append(str(ticker))

    change_context = build_13f_change_context(combined)
    proxy_return_context = build_13f_proxy_return_context(combined)
    futu_runtime = detect_futu_opend_status()

    for investor_id, limit in AUTO_POPULATE_HOLDINGS_FROM_13F.items():
        current_snapshot = (change_context.get(investor_id) or {}).get("current")
        if not current_snapshot:
            continue
        for row in _build_holdings_from_13f_snapshot(current_snapshot, limit=limit):
            ticker = row.get("ticker")
            if ticker:
                all_tickers.append(str(ticker))
    for investor_id, limit in HYBRID_LOOKTHROUGH_13F_BY_INVESTOR.items():
        current_snapshot = (change_context.get(investor_id) or {}).get("current")
        if not current_snapshot:
            continue
        for row in _build_holdings_from_13f_snapshot(current_snapshot, limit=limit):
            ticker = row.get("ticker")
            if ticker:
                all_tickers.append(str(ticker))

    quote_map, cache_hits, api_fetches = get_quote_map(
        all_tickers,
        cache_dir=args.cache_dir,
        ttl_hours=args.cache_ttl_hours,
        use_cache=not args.no_cache,
        futu_runtime=futu_runtime,
    )
    quote_source_breakdown: Dict[str, int] = {}
    for quote in quote_map.values():
        source = str(quote.get("source") or "unknown")
        quote_source_breakdown[source] = quote_source_breakdown.get(source, 0) + 1

    avatar_map = build_avatar_map(combined)
    normalized_investors = [
        normalize_investor(
            item,
            quote_map=quote_map,
            change_context=change_context,
            proxy_return_context=proxy_return_context,
            futu_runtime=futu_runtime,
        )
        for item in combined
    ]
    for item in normalized_investors:
        investor_id = str(item.get("id") or "")
        item["avatar_url"] = avatar_map.get(investor_id)
        if item.get("avatar_url"):
            if investor_id in INVESTOR_AVATAR_OVERRIDES:
                item["avatar_source"] = "PortfolioMoment public profile image"
            else:
                item["avatar_source"] = "Wikipedia REST summary API"
        else:
            item["avatar_source"] = "not_found"
    normalized_investors.sort(key=to_sort_key)
    for idx, item in enumerate(normalized_investors, start=1):
        item["profile_rank"] = idx

    interface_investor_covered = [
        item
        for item in normalized_investors
        if int((item.get("interface_quant") or {}).get("priced_asset_count") or 0) > 0
    ]
    interface_total_priced_assets = sum(
        int((item.get("interface_quant") or {}).get("priced_asset_count") or 0) for item in normalized_investors
    )
    interface_total_eligible_assets = sum(
        int((item.get("interface_quant") or {}).get("eligible_asset_count") or 0) for item in normalized_investors
    )

    opend_investor_covered = [
        item for item in normalized_investors if int((item.get("opend_quant") or {}).get("priced_asset_count") or 0) > 0
    ]
    opend_total_priced_assets = sum(
        int((item.get("opend_quant") or {}).get("priced_asset_count") or 0) for item in normalized_investors
    )

    payload = {
        "as_of_date": datetime.now(timezone.utc).date().isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "investor_count": len(normalized_investors),
        "investors": normalized_investors,
        "coverage_note": (
            "该资料库融合了可审计投资人、基金经理、管理层与公开披露交易主体。"
            "其中“公开披露交易”口径不等同于完整组合持仓。"
        ),
        "annualized_return_note": (
            "年化收益优先展示可审计历史口径；若缺失且存在13F代理口径，则展示13F价值序列CAGR代理。"
            "该代理并非审计净值年化，仅供参考。"
        ),
        "holdings_field_note": (
            "持仓字段包含：股票价格、持仓占比、持仓更新时间、持仓变动比例。"
            "若披露口径不支持，则明确标注“未披露/不适用”。"
        ),
        "price_data_source": "多源行情（Futu OpenD + Yahoo Finance via yfinance，按权限与可用性自动路由）",
        "futu_alignment_runtime": {
            "status": futu_runtime.get("status"),
            "endpoint": futu_runtime.get("endpoint"),
            "port": futu_runtime.get("port"),
            "note": futu_runtime.get("note"),
            "market_permissions": futu_runtime.get("market_permissions"),
            "market_probe_note": futu_runtime.get("market_probe_note"),
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "quote_source_breakdown": quote_source_breakdown,
        "interface_quant_summary": {
            "investor_covered_count": len(interface_investor_covered),
            "investor_total_count": len(normalized_investors),
            "total_priced_assets": interface_total_priced_assets,
            "total_eligible_assets": interface_total_eligible_assets,
            "asset_coverage_pct": (
                round(interface_total_priced_assets / interface_total_eligible_assets * 100.0, 2)
                if interface_total_eligible_assets > 0
                else None
            ),
            "covered_investor_ids": [str(item.get("id") or "") for item in interface_investor_covered],
            "note": "主指标：评估全部行情接口对投资人持仓样本的可报价覆盖能力。",
        },
        "opend_quant_summary": {
            "investor_covered_count": len(opend_investor_covered),
            "investor_total_count": len(normalized_investors),
            "total_priced_assets": opend_total_priced_assets,
            "covered_investor_ids": [str(item.get("id") or "") for item in opend_investor_covered],
            "note": "诊断指标：用于评估 OpenD 对当前投资人持仓样本的量化覆盖。",
        },
        "cache_policy": (
            "disabled"
            if args.no_cache
            else f"enabled; ttl_hours={args.cache_ttl_hours}; cache_hits={cache_hits}; api_fetches={api_fetches}"
        ),
        "source_legend": {
            **(base_payload.get("source_legend") or {}),
            **(additional_payload.get("source_legend") or {}),
            "sec_13f_disclosure_entity": "通过投资者关联披露实体（CIK）抓取 SEC 13F 持仓（美国长仓口径）",
            "13f_info_mirror": "13f.info 镜像（底层来源为 SEC 13F，官方接口异常时用于回退）",
            "13f_value_cagr_proxy": "13F披露组合市值序列推导的CAGR代理（非审计净值，会受资金流影响）",
        },
    }

    dump_json(args.output_file, payload)
    print(f"投资者资料库已生成: {args.output_file}")
    print(f"总人数: {len(normalized_investors)}")
    print(f"行情覆盖代码数: {len(quote_map)}")
    if args.no_cache:
        print("缓存: disabled")
    else:
        print(f"缓存: enabled (ttl={args.cache_ttl_hours}h, cache_hits={cache_hits}, api_fetches={api_fetches})")


if __name__ == "__main__":
    main()
