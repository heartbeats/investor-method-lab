#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
import yfinance as yf

from build_investor_profiles import detect_futu_opend_status

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STOCK_PROBE_SCRIPT = Path("/home/afu/.codex/skills/stock-data-fetch/scripts/probe_stock_sources.py")
STOCK_PROBE_OUTPUT = PROJECT_ROOT / "data" / "stock_provider_probe.json"


@dataclass
class SourceProbe:
    source_id: str
    name: str
    category: str
    markets: List[str]
    url: str
    update_frequency: str
    auth: str
    notes: str
    status: str
    detail: str
    latency_ms: int | None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.source_id,
            "name": self.name,
            "category": self.category,
            "markets": self.markets,
            "url": self.url,
            "update_frequency": self.update_frequency,
            "auth": self.auth,
            "notes": self.notes,
            "status": self.status,
            "detail": self.detail,
            "latency_ms": self.latency_ms,
        }


def _probe_http(url: str, expect_json_key: str | None = None, timeout: int = 20) -> tuple[str, str, int | None]:
    started = datetime.now(timezone.utc)
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as error:  # noqa: BLE001
        return "error", str(error)[:220], None
    latency_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

    if response.status_code >= 400:
        return "blocked", f"http {response.status_code}", latency_ms

    if expect_json_key:
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            return "error", "响应不是有效 JSON", latency_ms
        if expect_json_key in payload:
            return "ok", f"http {response.status_code}; json key `{expect_json_key}` 命中", latency_ms
        return "partial", f"http {response.status_code}; json key `{expect_json_key}` 未命中", latency_ms

    return "ok", f"http {response.status_code}", latency_ms


def _probe_yahoo() -> tuple[str, str, int | None]:
    started = datetime.now(timezone.utc)
    try:
        history = yf.Ticker("AAPL").history(period="5d", interval="1d", auto_adjust=False)
    except Exception as error:  # noqa: BLE001
        return "error", str(error)[:220], None
    latency_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    closes = history.get("Close")
    if closes is None or closes.dropna().empty:
        return "partial", "AAPL 无最新收盘价", latency_ms
    return "ok", "AAPL 行情可获取", latency_ms


def _run_stock_provider_probe() -> Dict[str, Any] | None:
    if not STOCK_PROBE_SCRIPT.exists():
        return None
    cmd = [
        "python3",
        str(STOCK_PROBE_SCRIPT),
        "--out",
        str(STOCK_PROBE_OUTPUT),
        "--skip-futu",
    ]
    secret_file = (os.getenv("IML_STOCK_SECRET_FILE") or "").strip()
    candidates = [secret_file, "/mnt/c/Users/Jarvis/Desktop/openclaw的秘密.txt"]
    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).exists():
            cmd.extend(["--secret-file", candidate])
            break
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:  # noqa: BLE001
        return None
    if completed.returncode != 0:
        return None
    if not STOCK_PROBE_OUTPUT.exists():
        return None
    try:
        return json.loads(STOCK_PROBE_OUTPUT.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _status_from_probe_counts(success_count: int, total: int) -> str:
    if total <= 0:
        return "partial"
    if success_count >= total:
        return "ok"
    if success_count > 0:
        return "partial"
    return "error"


def build_catalog() -> Dict[str, Any]:
    probes: List[SourceProbe] = []
    stock_probe = _run_stock_provider_probe()

    sec_status, sec_detail, sec_latency = _probe_http(
        "https://data.sec.gov/submissions/CIK0001067983.json",
        expect_json_key="filings",
    )
    probes.append(
        SourceProbe(
            source_id="sec_edgar_api",
            name="SEC EDGAR API",
            category="holdings_filings",
            markets=["US"],
            url="https://www.sec.gov/edgar/sec-api-documentation",
            update_frequency="near_real_time",
            auth="none",
            notes="13F/10K/10Q 等官方披露主源",
            status=sec_status,
            detail=sec_detail,
            latency_ms=sec_latency,
        )
    )

    f13_status, f13_detail, f13_latency = _probe_http("https://13f.info/manager/0001759760")
    probes.append(
        SourceProbe(
            source_id="13f_info_mirror",
            name="13f.info Mirror",
            category="holdings_filings",
            markets=["US"],
            url="https://13f.info",
            update_frequency="quarterly_13f",
            auth="none",
            notes="SEC 13F 镜像，用于官方接口异常时回退",
            status=f13_status,
            detail=f13_detail,
            latency_ms=f13_latency,
        )
    )

    yahoo_status, yahoo_detail, yahoo_latency = _probe_yahoo()
    if isinstance(stock_probe, dict):
        y = ((stock_probe.get("providers") or {}).get("yfinance") or {})
        mk = y.get("US") if isinstance(y, dict) else None
        if isinstance(mk, dict):
            success_count = int(mk.get("success_count") or 0)
            total = int(mk.get("total") or 0)
            yahoo_status = _status_from_probe_counts(success_count, total)
            yahoo_detail = (
                f"probe: US {success_count}/{total}; "
                f"p50={mk.get('p50_sec')}s; p95={mk.get('p95_sec')}s"
            )
            latency = mk.get("p50_sec")
            yahoo_latency = int(float(latency) * 1000) if latency is not None else None
    probes.append(
        SourceProbe(
            source_id="yahoo_yfinance",
            name="Yahoo Finance (yfinance)",
            category="quotes",
            markets=["US", "HK", "CN"],
            url="https://finance.yahoo.com",
            update_frequency="delayed_realtime",
            auth="none",
            notes="当前网页默认价格源之一",
            status=yahoo_status,
            detail=yahoo_detail,
            latency_ms=yahoo_latency,
        )
    )

    if isinstance(stock_probe, dict):
        providers = stock_probe.get("providers") or {}

        ak = providers.get("akshare_daily") if isinstance(providers, dict) else None
        if isinstance(ak, dict):
            ak_success = int(ak.get("success_count") or 0)
            ak_total = int(ak.get("total") or 0)
            probes.append(
                SourceProbe(
                    source_id="akshare_daily",
                    name="AkShare Daily",
                    category="quotes",
                    markets=["CN"],
                    url="https://akshare.akfamily.xyz/",
                    update_frequency="daily_or_intraday_pull",
                    auth="none",
                    notes="A股历史/日线补源，适合作为非实时回退。",
                    status=_status_from_probe_counts(ak_success, ak_total),
                    detail=(
                        f"probe: CN {ak_success}/{ak_total}; "
                        f"p50={ak.get('p50_sec')}s; p95={ak.get('p95_sec')}s"
                    ),
                    latency_ms=(
                        int(float(ak.get("p50_sec")) * 1000)
                        if ak.get("p50_sec") is not None
                        else None
                    ),
                )
            )

        av = providers.get("alpha_vantage") if isinstance(providers, dict) else None
        if isinstance(av, dict):
            av_global = av.get("global_quote") if isinstance(av.get("global_quote"), dict) else {}
            av_target = av.get("analyst_target") if isinstance(av.get("analyst_target"), dict) else {}
            av_status = "ok" if bool(av_global.get("ok")) else ("partial" if av.get("configured") else "disabled")
            probes.append(
                SourceProbe(
                    source_id="alpha_vantage",
                    name="Alpha Vantage",
                    category="quotes_fundamentals_external_reference",
                    markets=["US"],
                    url="https://www.alphavantage.co/",
                    update_frequency="api_rate_limited",
                    auth="api_key",
                    notes="免费额度严格，适合作为低频补源。",
                    status=av_status,
                    detail=(
                        f"global_quote_ok={av_global.get('ok')}; "
                        f"analyst_target_ok={av_target.get('ok')}; "
                        f"target_has_information={av_target.get('has_information')}"
                    ),
                    latency_ms=(
                        int(float(av_global.get("latency_sec")) * 1000)
                        if av_global.get("latency_sec") is not None
                        else None
                    ),
                )
            )

        fmp = providers.get("fmp") if isinstance(providers, dict) else None
        if isinstance(fmp, dict):
            fmp_quote = fmp.get("quote") if isinstance(fmp.get("quote"), dict) else {}
            fmp_target = (
                fmp.get("price_target_summary")
                if isinstance(fmp.get("price_target_summary"), dict)
                else {}
            )
            fmp_status = "ok" if bool(fmp_quote.get("ok")) else ("partial" if fmp.get("configured") else "disabled")
            probes.append(
                SourceProbe(
                    source_id="fmp_quote",
                    name="Financial Modeling Prep",
                    category="quotes_fundamentals_external_reference",
                    markets=["US", "global_partial"],
                    url="https://site.financialmodelingprep.com/",
                    update_frequency="api_rate_limited",
                    auth="api_key",
                    notes="可用于行情与目标价汇总；免费额度按天计数。",
                    status=fmp_status,
                    detail=(
                        f"quote_ok={fmp_quote.get('ok')}; "
                        f"target_summary_ok={fmp_target.get('ok')}"
                    ),
                    latency_ms=(
                        int(float(fmp_quote.get("latency_sec")) * 1000)
                        if fmp_quote.get("latency_sec") is not None
                        else None
                    ),
                )
            )

        ts = providers.get("tushare") if isinstance(providers, dict) else None
        if isinstance(ts, dict):
            ts_ok = bool(ts.get("ok"))
            ts_status = "ok" if ts_ok else ("partial" if ts.get("configured") else "disabled")
            probes.append(
                SourceProbe(
                    source_id="tushare_pro",
                    name="Tushare Pro",
                    category="quotes_fundamentals",
                    markets=["CN"],
                    url="https://tushare.pro/",
                    update_frequency="api_rate_limited",
                    auth="token+points",
                    notes="A股基础/财务重要补源；权限与频次受积分等级约束。",
                    status=ts_status,
                    detail=(
                        "probe ok"
                        if ts_ok
                        else f"probe_error={str(ts.get('error') or ts.get('error_type') or 'unknown')[:160]}"
                    ),
                    latency_ms=(
                        int(float(ts.get("latency_sec")) * 1000)
                        if ts.get("latency_sec") is not None
                        else None
                    ),
                )
            )

    futu_runtime = detect_futu_opend_status()
    futu_status = "ok" if futu_runtime.get("status") == "verified" else "partial"
    futu_detail = (
        f"{futu_runtime.get('note')} | "
        f"US={((futu_runtime.get('market_permissions') or {}).get('US'))}, "
        f"HK={((futu_runtime.get('market_permissions') or {}).get('HK'))}, "
        f"CN={((futu_runtime.get('market_permissions') or {}).get('CN'))}"
    )
    probes.append(
        SourceProbe(
            source_id="futu_opend",
            name="Futu OpenD",
            category="quotes_broker_data",
            markets=["US", "HK", "CN"],
            url="https://www.futunn.com/OpenAPI",
            update_frequency="realtime_with_permission",
            auth="broker_login+market_permission",
            notes="可用于实时报价、持仓、交易流水（需权限）",
            status=futu_status,
            detail=futu_detail,
            latency_ms=None,
        )
    )

    ark_status, ark_detail, ark_latency = _probe_http(
        "https://ark-funds.com/wp-content/fundsiteliterature/csv/ARKK_HOLDINGS.csv"
    )
    probes.append(
        SourceProbe(
            source_id="ark_etf_holdings",
            name="ARK ETF Holdings CSV",
            category="fund_holdings",
            markets=["US"],
            url="https://www.ark-funds.com/funds/arkk",
            update_frequency="daily",
            auth="none",
            notes="木头姐相关 ETF 日度持仓（当前环境可能被反爬阻断）",
            status=ark_status,
            detail=ark_detail,
            latency_ms=ark_latency,
        )
    )

    hkex_status, hkex_detail, hkex_latency = _probe_http("https://di.hkex.com.hk/di/notes/NSSrchPersonList.htm")
    probes.append(
        SourceProbe(
            source_id="hkex_di",
            name="HKEX Disclosure of Interests",
            category="insider_substantial_holder",
            markets=["HK"],
            url="https://di.hkex.com.hk/di/notes/NSSrchPersonList.htm",
            update_frequency="event_driven",
            auth="none",
            notes="港股董监高/大股东权益披露",
            status=hkex_status,
            detail=hkex_detail,
            latency_ms=hkex_latency,
        )
    )

    eastmoney_status, eastmoney_detail, eastmoney_latency = _probe_http(
        "https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f57,f58,f60",
        expect_json_key="data",
    )
    probes.append(
        SourceProbe(
            source_id="eastmoney_quote_api",
            name="Eastmoney Quote API",
            category="quotes",
            markets=["CN"],
            url="https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f57,f58,f60",
            update_frequency="intraday",
            auth="none",
            notes="A 股行情补源（公开接口，稳定性需监控）",
            status=eastmoney_status,
            detail=eastmoney_detail,
            latency_ms=eastmoney_latency,
        )
    )

    openinsider_status, openinsider_detail, openinsider_latency = _probe_http("http://openinsider.com/")
    probes.append(
        SourceProbe(
            source_id="openinsider",
            name="OpenInsider",
            category="insider_trades",
            markets=["US"],
            url="http://openinsider.com/",
            update_frequency="daily",
            auth="none",
            notes="SEC Form 4 聚合检索，可补高管交易信号",
            status=openinsider_status,
            detail=openinsider_detail,
            latency_ms=openinsider_latency,
        )
    )

    house_status, house_detail, house_latency = _probe_http("https://disclosures-clerk.house.gov/FinancialDisclosure/ViewReport")
    probes.append(
        SourceProbe(
            source_id="us_house_disclosure",
            name="US House Financial Disclosure",
            category="politician_disclosure",
            markets=["US"],
            url="https://disclosures-clerk.house.gov/FinancialDisclosure/ViewReport",
            update_frequency="event_driven",
            auth="none",
            notes="美国众议院官方财务披露/PTR 入口",
            status=house_status,
            detail=house_detail,
            latency_ms=house_latency,
        )
    )

    senate_status, senate_detail, senate_latency = _probe_http("https://efdsearch.senate.gov/search/home/")
    probes.append(
        SourceProbe(
            source_id="us_senate_disclosure",
            name="US Senate eFD Search",
            category="politician_disclosure",
            markets=["US"],
            url="https://efdsearch.senate.gov/search/home/",
            update_frequency="event_driven",
            auth="none",
            notes="美国参议院官方 eFD 披露检索入口",
            status=senate_status,
            detail=senate_detail,
            latency_ms=senate_latency,
        )
    )

    capitol_status, capitol_detail, capitol_latency = _probe_http("https://www.capitoltrades.com/trades?page=1")
    probes.append(
        SourceProbe(
            source_id="capitol_trades",
            name="Capitol Trades",
            category="politician_disclosure_aggregator",
            markets=["US"],
            url="https://www.capitoltrades.com/trades?page=1",
            update_frequency="daily",
            auth="none",
            notes="议员交易聚合页（辅助交叉核对）",
            status=capitol_status,
            detail=capitol_detail,
            latency_ms=capitol_latency,
        )
    )

    status_counts: Dict[str, int] = {}
    for item in probes:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    return {
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "stock_provider_probe": (
            {
                "script": str(STOCK_PROBE_SCRIPT),
                "output_file": str(STOCK_PROBE_OUTPUT),
                "generated_at": stock_probe.get("generated_at"),
            }
            if isinstance(stock_probe, dict)
            else {
                "script": str(STOCK_PROBE_SCRIPT),
                "output_file": str(STOCK_PROBE_OUTPUT),
                "generated_at": None,
                "note": "probe_unavailable_or_failed",
            }
        ),
        "source_count": len(probes),
        "status_counts": status_counts,
        "sources": [item.to_dict() for item in probes],
        "recommendation": [
            "优先把 status=ok/partial 的源接入自动任务，status=blocked 的源做浏览器会话下载或人工补录。",
            "对 OpenD 维持市场级权限监控（US/HK/CN），避免误判“已可量化”。",
            "对议员披露源建立双源交叉（官方入口 + 聚合站）以降低漏单风险。",
        ],
    }


def main() -> None:
    payload = build_catalog()
    out_path = PROJECT_ROOT / "data" / "data_source_catalog.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"data source catalog generated: {out_path}")
    print(f"sources: {payload['source_count']} | status_counts: {payload['status_counts']}")


if __name__ == "__main__":
    main()
