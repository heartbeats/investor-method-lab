(function () {
  const FILES = {
    stockProfiles: "../data/stock_profiles.json",
    opportunities: {
      sample: "../data/opportunities.sample.csv",
      real: "../data/opportunities.real.csv",
      real3: "../data/opportunities.real_3markets.csv",
    },
    traces: {
      sample: "../output/method_decision_trace.json",
      real: "../output/method_decision_trace_real.json",
      real3: "../output/method_decision_trace_real_3markets.json",
    },
  };

  const TIER_LABELS = {
    core: "核心池",
    watch: "观察池",
    tactical: "战术池",
    rejected: "淘汰",
  };

  const CONFIDENCE_LABELS = {
    high_disclosed: "高（年报/10-K披露）",
    medium_disclosed: "中（财报/分部披露）",
    medium_estimated: "中（披露+估算）",
    low_estimated: "低（估算口径）",
    unknown: "未知",
  };

  function qs(selector) {
    return document.querySelector(selector);
  }

  function escapeHtml(text) {
    return String(text ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function uniqueNonEmpty(values) {
    return [...new Set((values || []).map((item) => String(item || "").trim()).filter(Boolean))];
  }

  function getParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      ticker: (params.get("ticker") || "").trim().toUpperCase(),
      pack: (params.get("pack") || "real3").trim(),
      dcfBase: (params.get("dcf_base") || "").trim(),
    };
  }

  function formatNum(value, digits = 2) {
    if (value === null || value === undefined || value === "") return "-";
    const n = Number(value);
    if (!Number.isFinite(n)) return "-";
    return n.toFixed(digits);
  }

  function formatPct(value, digits = 2) {
    if (value === null || value === undefined || value === "") return "-";
    const n = Number(value);
    if (!Number.isFinite(n)) return "-";
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(digits)}%`;
  }

  function formatSignedPct(decimalValue, digits = 2) {
    if (decimalValue === null || decimalValue === undefined || decimalValue === "") return "-";
    const n = Number(decimalValue);
    if (!Number.isFinite(n)) return "-";
    const sign = n > 0 ? "+" : "";
    return `${sign}${(n * 100).toFixed(digits)}%`;
  }

  function formatRatioPct(decimalValue, digits = 2) {
    if (decimalValue === null || decimalValue === undefined || decimalValue === "") return "-";
    const n = Number(decimalValue);
    if (!Number.isFinite(n)) return "-";
    return `${(n * 100).toFixed(digits)}%`;
  }

  function formatDateTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escapeHtml(value);
    return date.toLocaleString("zh-CN", { hour12: false });
  }

  function toNumber(value) {
    if (value === null || value === undefined || value === "") return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function canonicalTicker(raw) {
    const ticker = String(raw || "").trim().toUpperCase();
    if (!ticker) return "";

    const prefixed = ticker.match(/^(US|HK|SH|SZ)\.([A-Z0-9]+)$/);
    if (prefixed) {
      const market = prefixed[1];
      const code = prefixed[2];
      if (market === "HK") return `${code.padStart(5, "0")}.HK`;
      if (market === "SH") return `${code}.SS`;
      if (market === "SZ") return `${code}.SZ`;
      return code;
    }

    const hkMatch = ticker.match(/^(\d{1,5})\.HK$/);
    if (hkMatch) return `${hkMatch[1].padStart(5, "0")}.HK`;

    return ticker;
  }

  function buildSymbolAliases(raw) {
    const value = String(raw || "").trim().toUpperCase();
    if (!value) return [];

    const aliases = new Set([value]);
    const canonical = canonicalTicker(value);
    if (canonical) aliases.add(canonical);

    if (/^[A-Z]+$/.test(canonical)) {
      aliases.add(`US.${canonical}`);
    }

    const hkMatch = canonical.match(/^(\d{5})\.HK$/);
    if (hkMatch) aliases.add(`HK.${hkMatch[1]}`);

    const shMatch = canonical.match(/^(\d{6})\.SS$/);
    if (shMatch) aliases.add(`SH.${shMatch[1]}`);

    const szMatch = canonical.match(/^(\d{6})\.SZ$/);
    if (szMatch) aliases.add(`SZ.${szMatch[1]}`);

    return [...aliases];
  }

  function registerLookup(map, value, candidates) {
    uniqueNonEmpty(candidates).forEach((candidate) => {
      buildSymbolAliases(candidate).forEach((alias) => {
        map.set(alias, value);
      });
    });
  }

  async function fetchJson(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) return null;
      return await res.json();
    } catch (_err) {
      return null;
    }
  }

  async function fetchText(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) return null;
      return await res.text();
    } catch (_err) {
      return null;
    }
  }

  function renderNotFound(ticker) {
    document.body.innerHTML = `
      <main class="detail-page">
        <section class="panel">
          <h1>未找到股票资料</h1>
          <p class="muted">ticker=${escapeHtml(ticker || "空")} 无可用数据。</p>
          <p><a href="./index.html">返回总览页</a></p>
        </section>
      </main>
    `;
  }

  function parseCsv(text) {
    if (!text) return [];
    const rows = [];
    let row = [];
    let value = "";
    let inQuotes = false;

    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      const next = text[i + 1];
      if (ch === '"') {
        if (inQuotes && next === '"') {
          value += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === "," && !inQuotes) {
        row.push(value);
        value = "";
      } else if ((ch === "\n" || ch === "\r") && !inQuotes) {
        if (ch === "\r" && next === "\n") i += 1;
        row.push(value);
        value = "";
        if (row.some((item) => item !== "")) rows.push(row);
        row = [];
      } else {
        value += ch;
      }
    }

    if (value.length > 0 || row.length > 0) {
      row.push(value);
      if (row.some((item) => item !== "")) rows.push(row);
    }

    if (!rows.length) return [];
    const header = rows[0];
    return rows.slice(1).map((line) => {
      const obj = {};
      header.forEach((key, idx) => {
        obj[key] = line[idx] ?? "";
      });
      return obj;
    });
  }

  function parseNoteFields(note) {
    const text = String(note || "");
    const closeMatch = text.match(/close=([0-9]+(?:\.[0-9]+)?)/i);
    const targetMatch = text.match(/target=([0-9]+(?:\.[0-9]+)?)/i);
    const dateMatch = text.match(/real-data@(\d{4}-\d{2}-\d{2})/i);
    const fvSourceMatch = text.match(/fv_source=([^|]+)/i);
    const upsideMatch = text.match(/upside=([-+]?[0-9]+(?:\.[0-9]+)?)%/i);

    return {
      close: toNumber(closeMatch?.[1]),
      target: toNumber(targetMatch?.[1]),
      priceDate: dateMatch?.[1] || null,
      fairValueSource: fvSourceMatch?.[1]?.trim() || null,
      upsidePct: toNumber(upsideMatch?.[1]),
    };
  }

  function inferMarketFromTicker(ticker) {
    const value = canonicalTicker(ticker);
    if (value.endsWith(".SS") || value.endsWith(".SZ")) return "A";
    if (value.endsWith(".HK")) return "HK";
    return "US";
  }

  function buildOpportunityValuation(opportunityRow) {
    if (!opportunityRow) return null;
    const p2fv = toNumber(opportunityRow.price_to_fair_value);
    const fairValue = toNumber(opportunityRow.fair_value);
    const targetMeanPrice = toNumber(opportunityRow.target_mean_price);

    return {
      price_to_fair_value: p2fv,
      fair_value: fairValue,
      target_mean_price: targetMeanPrice,
      margin_of_safety_fv_pct: p2fv === null ? null : (1 - p2fv) * 100,
      quality_score: toNumber(opportunityRow.quality_score),
      growth_score: toNumber(opportunityRow.growth_score),
      momentum_score: toNumber(opportunityRow.momentum_score),
      catalyst_score: toNumber(opportunityRow.catalyst_score),
      risk_score: toNumber(opportunityRow.risk_score),
      certainty_score: toNumber(opportunityRow.certainty_score),
      valuation_source: opportunityRow.valuation_source || "",
      valuation_source_detail: opportunityRow.valuation_source_detail || "",
      note: opportunityRow.note || "",
    };
  }

  function buildFallbackProfile(ticker, opportunityRow) {
    if (!opportunityRow) return null;
    const noteFields = parseNoteFields(opportunityRow.note);
    const valuation = buildOpportunityValuation(opportunityRow);
    const market = opportunityRow.market || inferMarketFromTicker(ticker);
    const displayName = opportunityRow.name || ticker;
    const currencyByMarket = {
      A: "CNY",
      HK: "HKD",
      US: "USD",
    };

    return {
      ticker: canonicalTicker(ticker),
      name: displayName,
      name_cn: displayName,
      symbol: ticker,
      dcf_symbol: ticker.startsWith("US.") || ticker.startsWith("HK.") || ticker.startsWith("SH.") || ticker.startsWith("SZ.")
        ? ticker
        : null,
      market,
      sector: opportunityRow.sector || "-",
      industry: opportunityRow.industry || "-",
      website: null,
      business_intro: "当前数据源未提供结构化公司业务介绍，已展示可核验的行情与估值字段。",
      products_intro: "当前数据源未提供结构化产品介绍。",
      current_price: noteFields.close,
      currency: currencyByMarket[market] || "-",
      price_as_of: noteFields.priceDate,
      target_mean_price: toNumber(opportunityRow.target_mean_price) ?? noteFields.target,
      trailing_pe: null,
      forward_pe: null,
      price_to_book: null,
      enterprise_to_ebitda: null,
      market_cap: null,
      source: "opportunities fallback",
      valuation_real3: valuation,
      valuation_real: valuation,
      note: opportunityRow.note || "",
    };
  }

  function enrichProfile(baseProfile, ticker, opportunityRow) {
    if (!baseProfile) return buildFallbackProfile(ticker, opportunityRow);

    const profile = { ...baseProfile };
    profile.ticker = profile.ticker || canonicalTicker(ticker);
    profile.symbol = profile.symbol || ticker || profile.ticker;
    profile.market = profile.market || opportunityRow?.market || inferMarketFromTicker(ticker);

    if ((!profile.name || profile.name === ticker) && opportunityRow?.name) {
      profile.name = opportunityRow.name;
    }
    if (!profile.name_cn && opportunityRow?.name) {
      profile.name_cn = opportunityRow.name;
    }
    if (!profile.sector && opportunityRow?.sector) {
      profile.sector = opportunityRow.sector;
    }
    if (!profile.industry && opportunityRow?.industry) {
      profile.industry = opportunityRow.industry;
    }

    const noteFields = parseNoteFields(opportunityRow?.note);
    if (!Number.isFinite(Number(profile.current_price))) {
      profile.current_price = noteFields.close;
    }
    if (!profile.price_as_of) {
      profile.price_as_of = noteFields.priceDate;
    }
    if (!Number.isFinite(Number(profile.target_mean_price))) {
      const target = toNumber(opportunityRow?.target_mean_price);
      profile.target_mean_price = target ?? noteFields.target;
    }
    if (!profile.business_intro) {
      profile.business_intro = "当前数据源未提供结构化公司业务介绍，已展示可核验的行情与估值字段。";
    }
    if (!profile.products_intro) {
      profile.products_intro = "当前数据源未提供结构化产品介绍。";
    }
    if (!profile.source) {
      profile.source = "stock_profiles + opportunities fallback";
    }

    const oppValuation = buildOpportunityValuation(opportunityRow);
    if (!profile.valuation_real3 && oppValuation) {
      profile.valuation_real3 = oppValuation;
    }
    if (!profile.valuation_real && oppValuation) {
      profile.valuation_real = oppValuation;
    }

    return profile;
  }

  function explainConfidence(rawValue) {
    const key = String(rawValue || "unknown").trim();
    const label = CONFIDENCE_LABELS[key] || key || CONFIDENCE_LABELS.unknown;
    const estimated = key.includes("estimated");
    const note = estimated
      ? "当前包含估算成分，优先用于研究与跟踪，不建议直接作为交易定量输入。"
      : "当前以公司披露口径为主，适合做方法论验证与对比。";
    return { key, label, estimated, note };
  }

  function renderSourcesHtml(sources) {
    if (!Array.isArray(sources) || !sources.length) return "<p class=\"muted\">暂无来源链接。</p>";
    const items = sources
      .map((item) => {
        const title = escapeHtml(item?.title || "未命名来源");
        const url = String(item?.url || "").trim();
        if (!url) return `<li>${title}</li>`;
        return `<li><a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${title}</a></li>`;
      })
      .join("");
    return `<ul class="source-list">${items}</ul>`;
  }

  function renderProductBreakdown(profile) {
    const rows = Array.isArray(profile.product_revenue_breakdown) ? profile.product_revenue_breakdown : [];
    if (!rows.length) {
      return `<p class="muted">当前未拿到结构化产品占比披露，已展示已有文字说明。</p>`;
    }
    const body = rows
      .map((item, idx) => {
        const product = escapeHtml(item?.product || "-");
        const share = escapeHtml(item?.revenue_share || "-");
        const customers = escapeHtml(item?.customers || "-");
        const moat = escapeHtml(item?.core_competitiveness || "-");
        return `
          <tr>
            <td>${idx + 1}</td>
            <td>${product}</td>
            <td>${share}</td>
            <td>${customers}</td>
            <td>${moat}</td>
          </tr>
        `;
      })
      .join("");

    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>产品/业务</th>
              <th>收入占比</th>
              <th>主要客户</th>
              <th>核心竞争力</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>
      </div>
    `;
  }

  function getDcfBaseCandidates(preferredBase) {
    let storedBase = "";
    try {
      storedBase = window.localStorage.getItem("iml_dcf_base") || "";
    } catch (_err) {
      storedBase = "";
    }

    return uniqueNonEmpty([preferredBase, storedBase, "http://127.0.0.1:8000", "http://localhost:8000"]);
  }

  function resolveDcfSymbol(profile, ticker) {
    const direct = uniqueNonEmpty([profile?.dcf_symbol, profile?.symbol, ticker]);
    const prefixed = direct.find((item) => /^(US|HK|SH|SZ)\./.test(item));
    if (prefixed) return prefixed.toUpperCase();

    const canonical = canonicalTicker(direct[0] || ticker);
    if (!canonical) return null;

    const hkMatch = canonical.match(/^(\d{5})\.HK$/);
    if (hkMatch) return `HK.${hkMatch[1]}`;

    const shMatch = canonical.match(/^(\d{6})\.SS$/);
    if (shMatch) return `SH.${shMatch[1]}`;

    const szMatch = canonical.match(/^(\d{6})\.SZ$/);
    if (szMatch) return `SZ.${szMatch[1]}`;

    return `US.${canonical}`;
  }

  function resolvePriceChangePct(profile, quote) {
    const candidates = [
      profile?.price_change_pct,
      profile?.change_pct,
      profile?.daily_change_pct,
      profile?.quote_change_pct,
      quote?.change_pct,
      quote?.pct_change,
    ];
    const hit = candidates.map((value) => toNumber(value)).find((value) => value !== null);
    return hit === undefined ? null : hit;
  }

  async function fetchDcfOverview(dcfSymbol, preferredBase) {
    if (!dcfSymbol) {
      return {
        overview: null,
        quote: null,
        base: null,
        refreshed: false,
        error: "未找到可用的 DCF symbol。",
      };
    }

    const attempts = [];
    const bases = getDcfBaseCandidates(preferredBase);

    for (const base of bases) {
      for (const refresh of [true, false]) {
        const overviewUrl = `${base}/v1/company/${encodeURIComponent(dcfSymbol)}?refresh_valuation=${refresh ? "true" : "false"}`;
        try {
          const overviewResp = await fetch(overviewUrl);
          if (!overviewResp.ok) {
            attempts.push(`${base}(${refresh ? "refresh" : "cache"}) -> HTTP ${overviewResp.status}`);
            continue;
          }
          const overview = await overviewResp.json();

          let quote = null;
          try {
            const quoteResp = await fetch(`${base}/v1/quotes?symbols=${encodeURIComponent(dcfSymbol)}&refresh=true`);
            if (quoteResp.ok) {
              const quoteRows = await quoteResp.json();
              quote = Array.isArray(quoteRows) ? quoteRows[0] || null : null;
            }
          } catch (_err) {
            quote = null;
          }

          return {
            overview,
            quote,
            base,
            refreshed: refresh,
            error: null,
          };
        } catch (error) {
          attempts.push(`${base}(${refresh ? "refresh" : "cache"}) -> ${error.message || "fetch failed"}`);
        }
      }
    }

    return {
      overview: null,
      quote: null,
      base: null,
      refreshed: false,
      error: attempts.join("；") || "DCF API 不可用。",
    };
  }

  function findMappedRow(map, ticker) {
    const aliases = buildSymbolAliases(ticker);
    return aliases.map((alias) => map.get(alias)).find(Boolean) || null;
  }

  function buildDisplayName(profile) {
    if (profile.name_cn && profile.name && profile.name_cn !== profile.name) {
      return `${profile.name_cn} / ${profile.name}`;
    }
    return profile.name_cn || profile.name || profile.ticker || "-";
  }

  function buildCoreMetricCard(label, value, meta, className = "") {
    return `
      <article class="core-metric-card">
        <p class="core-metric-label">${escapeHtml(label)}</p>
        <p class="core-metric-value ${escapeHtml(className)}">${value}</p>
        <p class="core-metric-meta">${meta}</p>
      </article>
    `;
  }

  function buildValuationKpiCard(label, value, meta) {
    return `
      <article class="valuation-kpi-card">
        <h3>${escapeHtml(label)}</h3>
        <p class="valuation-kpi-value">${value}</p>
        <p class="core-metric-meta">${meta}</p>
      </article>
    `;
  }

  function renderCorePanel(profile, dcfData) {
    const overview = dcfData?.overview || {};
    const quote = dcfData?.quote || null;
    const valuation = overview.latest_valuation || null;
    const policy = overview.policy || null;
    const snapshot = overview.latest_snapshot || null;
    const currentPrice = toNumber(quote?.price) ?? toNumber(valuation?.price) ?? toNumber(profile.current_price);
    const currentPriceText = currentPrice === null ? "-" : `${formatNum(currentPrice, 2)} ${escapeHtml(profile.currency || overview.company?.currency || "")}`;
    const changePct = resolvePriceChangePct(profile, quote);
    const changeText = changePct === null
      ? '<span class="metric-pending">待接入</span>'
      : escapeHtml(formatPct(changePct, 2));
    const changeClass = changePct === null ? "" : changePct > 0 ? "positive" : changePct < 0 ? "negative" : "";
    const mosText = valuation ? escapeHtml(formatSignedPct(valuation.mos_base, 2)) : "-";
    const baseValueText = valuation ? `${escapeHtml(formatNum(valuation.iv_base, 2))} ${escapeHtml(profile.currency || "")}` : "-";
    const refreshText = quote?.timestamp ? formatDateTime(quote.timestamp) : valuation?.calculated_at ? formatDateTime(valuation.calculated_at) : escapeHtml(profile.price_as_of || "-");
    const priceMeta = quote?.source
      ? `报价源 ${escapeHtml(quote.source)} · 更新时间 ${escapeHtml(refreshText)}`
      : `更新时间 ${escapeHtml(refreshText)}`;
    const codeText = uniqueNonEmpty([profile.ticker, profile.symbol, profile.dcf_symbol]).slice(0, 2).join(" / ");
    const marketText = profile.market || inferMarketFromTicker(profile.ticker || profile.symbol);
    const dataChip = dcfData?.base ? `DCF已联动` : `仅画像层`;
    const intro = profile.problem_solved_zh || profile.business_intro_zh || profile.business_intro || "当前展示公司画像、估值总览和方法轨迹。";

    qs("#stock-core-panel").innerHTML = `
      <div class="stock-core-copy">
        <div>
          <p class="eyebrow">Stock Detail</p>
          <h1>${escapeHtml(buildDisplayName(profile))}</h1>
          <p class="subtitle">${escapeHtml(`${marketText} | ${profile.sector || "-"} | ${profile.industry || "-"}`)}</p>
        </div>
        <div class="stock-code-row">
          <span class="stock-code-chip">代码 ${escapeHtml(codeText || "-")}</span>
          <span class="stock-data-chip">${escapeHtml(dataChip)}</span>
          ${
            snapshot?.fiscal_year
              ? `<span class="stock-data-chip">财报口径 FY${escapeHtml(String(snapshot.fiscal_year))}</span>`
              : ""
          }
          ${
            policy?.policy_id
              ? `<span class="stock-data-chip">模板 ${escapeHtml(policy.policy_id)}</span>`
              : ""
          }
        </div>
        <p class="stock-core-note">${escapeHtml(intro)}</p>
      </div>
      <div class="stock-core-grid">
        ${buildCoreMetricCard("最新价", escapeHtml(currentPriceText), priceMeta)}
        ${buildCoreMetricCard("日内涨跌幅", changeText, "当前详情页数据合同尚未回传该字段。", changeClass)}
        ${buildCoreMetricCard("当前安全边际", mosText, valuation ? `基于中性估值 ${escapeHtml(formatNum(valuation.iv_base, 2))}` : "待接入 DCF 主链路。", valuation?.mos_base > 0 ? "positive" : valuation?.mos_base < 0 ? "negative" : "")}
        ${buildCoreMetricCard("中性估值", escapeHtml(baseValueText), policy ? `折现率 R ${escapeHtml(formatRatioPct(policy.r, 2))} · g2 ${escapeHtml(formatRatioPct(policy.g_terminal, 2))}` : "当前未拿到折现模板。")}
      </div>
    `;
  }

  function renderValuationPanel(profile, opportunityRow, dcfData) {
    const overview = dcfData?.overview || {};
    const quote = dcfData?.quote || null;
    const valuation = overview.latest_valuation || null;
    const policy = overview.policy || null;
    const snapshot = overview.latest_snapshot || null;
    const parameterLibrary = overview.parameter_library || null;
    const fallbackVal = profile.valuation_real3 || profile.valuation_real || buildOpportunityValuation(opportunityRow) || {};
    const currentPrice = toNumber(quote?.price) ?? toNumber(valuation?.price) ?? toNumber(profile.current_price);
    const baseValue = toNumber(valuation?.iv_base) ?? toNumber(fallbackVal.fair_value) ?? toNumber(profile.target_mean_price);
    const fallbackMosPct = toNumber(fallbackVal.margin_of_safety_fv_pct);
    const mosRatio = valuation ? toNumber(valuation.mos_base) : fallbackMosPct === null ? null : fallbackMosPct / 100;
    const priceToFair = valuation && currentPrice !== null && baseValue
      ? currentPrice / baseValue
      : toNumber(fallbackVal.price_to_fair_value);
    const targetMean = toNumber(profile.target_mean_price) ?? toNumber(fallbackVal.target_mean_price);

    qs("#stock-valuation-panel").innerHTML = `
      <div class="panel-head">
        <h2>估值总览</h2>
        <p>把估值总览、估值拆解和增长与隐含预期合成一层，先看结论，再看推导。</p>
      </div>

      <div class="valuation-highlight-grid">
        ${buildValuationKpiCard("当前价", currentPrice === null ? "-" : `${escapeHtml(formatNum(currentPrice, 2))} ${escapeHtml(profile.currency || "")}`, quote?.timestamp ? `报价时间 ${escapeHtml(formatDateTime(quote.timestamp))}` : "当前价格时间待补")}
        ${buildValuationKpiCard("中性估值", baseValue === null ? "-" : `${escapeHtml(formatNum(baseValue, 2))} ${escapeHtml(profile.currency || "")}`, valuation?.calculated_at ? `估值刷新 ${escapeHtml(formatDateTime(valuation.calculated_at))}` : "估值刷新时间待补")}
        ${buildValuationKpiCard("安全边际(FV)", mosRatio === null ? "-" : escapeHtml(formatSignedPct(mosRatio, 2)), priceToFair === null ? "Price / Fair Value 待补" : `Price / FV ${escapeHtml(formatNum(priceToFair, 4))}`)}
        ${buildValuationKpiCard("折现率 R", policy ? escapeHtml(formatRatioPct(policy.r, 2)) : "-", policy ? `g2 ${escapeHtml(formatRatioPct(policy.g_terminal, 2))} · ${escapeHtml(policy.policy_id)}` : "当前未拿到折现模板")}
      </div>

      <div class="section-split-grid">
        <article class="section-card">
          <h3>估值拆解</h3>
          <dl class="kv-list">
            <div class="kv-row">
              <dt>悲/中/乐估值</dt>
              <dd>${
                valuation
                  ? `${escapeHtml(formatNum(valuation.iv_bear, 2))} / ${escapeHtml(formatNum(valuation.iv_base, 2))} / ${escapeHtml(formatNum(valuation.iv_bull, 2))}`
                  : "-"
              }</dd>
            </div>
            <div class="kv-row">
              <dt>Price / Fair Value</dt>
              <dd>${priceToFair === null ? "-" : escapeHtml(formatNum(priceToFair, 4))}</dd>
            </div>
            <div class="kv-row">
              <dt>分析师目标均值</dt>
              <dd>${targetMean === null ? "-" : `${escapeHtml(formatNum(targetMean, 2))} ${escapeHtml(profile.currency || "")}`}</dd>
            </div>
            <div class="kv-row">
              <dt>20% / 40%提醒价</dt>
              <dd>${
                valuation
                  ? `${escapeHtml(formatNum(valuation.alert_price_20, 2))} / ${escapeHtml(formatNum(valuation.alert_price_40, 2))}`
                  : "-"
              }</dd>
            </div>
            <div class="kv-row">
              <dt>终值占比</dt>
              <dd>${valuation ? escapeHtml(formatSignedPct(valuation.terminal_ratio_base, 2)) : "-"}</dd>
            </div>
            <div class="kv-row">
              <dt>参数库基线</dt>
              <dd>${
                parameterLibrary
                  ? `参考价 ${escapeHtml(formatNum(parameterLibrary.reference_price, 2))} · 三档增长 ${escapeHtml(formatRatioPct(parameterLibrary.growth_scenarios.bear, 2))} / ${escapeHtml(formatRatioPct(parameterLibrary.growth_scenarios.base, 2))} / ${escapeHtml(formatRatioPct(parameterLibrary.growth_scenarios.bull, 2))}`
                  : "当前未建立参数库基线或页面尚未拿到该数据。"
              }</dd>
            </div>
          </dl>
        </article>

        <article class="section-card">
          <h3>增长与隐含预期</h3>
          <dl class="kv-list">
            <div class="kv-row">
              <dt>设定增长（悲/中/乐）</dt>
              <dd>${
                valuation
                  ? `${escapeHtml(formatRatioPct(valuation.g_bear, 2))} / ${escapeHtml(formatRatioPct(valuation.g_base, 2))} / ${escapeHtml(formatRatioPct(valuation.g_bull, 2))}`
                  : parameterLibrary
                    ? `${escapeHtml(formatRatioPct(parameterLibrary.growth_scenarios.bear, 2))} / ${escapeHtml(formatRatioPct(parameterLibrary.growth_scenarios.base, 2))} / ${escapeHtml(formatRatioPct(parameterLibrary.growth_scenarios.bull, 2))}`
                    : "-"
              }</dd>
            </div>
            <div class="kv-row">
              <dt>当前价隐含增长</dt>
              <dd>${valuation ? escapeHtml(formatSignedPct(valuation.implied_growth_at_price, 2)) : "-"}</dd>
            </div>
            <div class="kv-row">
              <dt>20%价隐含增长</dt>
              <dd>${valuation ? escapeHtml(formatSignedPct(valuation.implied_growth_at_20, 2)) : "-"}</dd>
            </div>
            <div class="kv-row">
              <dt>40%价隐含增长</dt>
              <dd>${valuation ? escapeHtml(formatSignedPct(valuation.implied_growth_at_40, 2)) : "-"}</dd>
            </div>
            <div class="kv-row">
              <dt>长期增长 g2</dt>
              <dd>${policy ? escapeHtml(formatRatioPct(policy.g_terminal, 2)) : "-"}</dd>
            </div>
            <div class="kv-row">
              <dt>财报/快照口径</dt>
              <dd>${
                snapshot
                  ? `FY${escapeHtml(String(snapshot.fiscal_year))} · ${escapeHtml(snapshot.source || "-")} · ${escapeHtml(snapshot.status || "-")}`
                  : "当前未拿到快照。"
              }</dd>
            </div>
          </dl>
        </article>
      </div>

      <div class="opportunity-detail">
        <h3 class="section-subhead">估值补充</h3>
        <div class="detail-grid">
          <article class="detail-item">
            <h4>Trailing PE / Forward PE</h4>
            <p>${escapeHtml(formatNum(profile.trailing_pe, 2))} / ${escapeHtml(formatNum(profile.forward_pe, 2))}</p>
          </article>
          <article class="detail-item">
            <h4>Price to Book / EV/EBITDA</h4>
            <p>${escapeHtml(formatNum(profile.price_to_book, 2))} / ${escapeHtml(formatNum(profile.enterprise_to_ebitda, 2))}</p>
          </article>
          <article class="detail-item">
            <h4>市值</h4>
            <p>${escapeHtml(formatNum(profile.market_cap, 0))}</p>
          </article>
          <article class="detail-item">
            <h4>估值链路状态</h4>
            <p>${
              dcfData?.overview
                ? `${escapeHtml(dcfData.base || "-")} · ${dcfData.refreshed ? "实时刷新" : "缓存回退"}`
                : "DCF 主链路未接通，当前只展示静态画像可提供的估值字段。"
            }</p>
          </article>
        </div>
      </div>
    `;
  }

  function renderBusinessPanel(profile, dcfData) {
    const overview = dcfData?.overview || {};
    const quote = dcfData?.quote || null;
    const valuation = overview.latest_valuation || null;
    const policy = overview.policy || null;
    const snapshot = overview.latest_snapshot || null;
    const confidence = explainConfidence(profile.intro_data_confidence || "unknown");
    const businessIntro =
      profile.business_intro_zh ||
      profile.business_intro ||
      "当前未接入该股票的中文公司介绍模板（已保留价格、估值与方法论轨迹数据）。";
    const howItMakesMoney =
      profile.how_it_makes_money_zh ||
      profile.products_intro_zh ||
      profile.products_intro ||
      "当前未接入该股票的收入结构说明。";
    const problemSolved = profile.problem_solved_zh || "待补齐。";
    const payers = profile.payers_zh || "待补齐。";
    const users = profile.users_zh || "待补齐。";
    const keyCustomers = profile.key_customers_zh || "待补齐。";
    const coreCompetitiveness = profile.core_competitiveness_zh || "待补齐。";
    const revenueShareNote = profile.revenue_share_note_zh || "待补齐。";

    qs("#stock-business-panel").innerHTML = `
      <div class="panel-head">
        <h2>公司与产品 / 最新动态</h2>
        <p>先看这家公司做什么、怎么赚钱，再看最新一次可核验的跟踪更新。</p>
      </div>

      <div class="section-split-grid">
        <article class="section-card">
          <h3>公司在做什么</h3>
          <p>${escapeHtml(businessIntro)}</p>
          <p class="section-subnote">解决的问题：${escapeHtml(problemSolved)}</p>
        </article>
        <article class="section-card">
          <h3>怎么赚钱</h3>
          <p>${escapeHtml(howItMakesMoney)}</p>
          <p class="section-subnote">披露期 ${escapeHtml(profile.intro_fiscal_period || "待补齐")} · 置信度 ${escapeHtml(confidence.label)}</p>
        </article>
      </div>

      <div class="opportunity-detail">
        <div class="detail-grid">
          <article class="detail-item">
            <h4>谁在付钱</h4>
            <p>${escapeHtml(payers)}</p>
          </article>
          <article class="detail-item">
            <h4>谁在使用</h4>
            <p>${escapeHtml(users)}</p>
          </article>
          <article class="detail-item">
            <h4>主要客户</h4>
            <p>${escapeHtml(keyCustomers)}</p>
          </article>
          <article class="detail-item">
            <h4>核心竞争力</h4>
            <p>${escapeHtml(coreCompetitiveness)}</p>
          </article>
          <article class="detail-item">
            <h4>收入占比口径说明</h4>
            <p>${escapeHtml(revenueShareNote)}</p>
          </article>
          <article class="detail-item">
            <h4>当前口径风险</h4>
            <p>${escapeHtml(confidence.note)}</p>
          </article>
        </div>
      </div>

      <div class="opportunity-detail">
        <h3 class="section-subhead">产品与收入结构</h3>
        ${renderProductBreakdown(profile)}
      </div>

      <div class="opportunity-detail">
        <h3 class="section-subhead">最新动态</h3>
        <div class="dynamic-grid">
          <article class="dynamic-card">
            <h3>最新估值刷新</h3>
            <ul class="source-meta-list">
              <li><strong>现价：</strong>${quote?.price !== undefined && quote?.price !== null ? escapeHtml(formatNum(quote.price, 2)) : valuation ? escapeHtml(formatNum(valuation.price, 2)) : "-"}</li>
              <li><strong>刷新时间：</strong>${escapeHtml(quote?.timestamp ? formatDateTime(quote.timestamp) : valuation?.calculated_at ? formatDateTime(valuation.calculated_at) : "-")}</li>
              <li><strong>来源：</strong>${escapeHtml(quote?.source || dcfData?.base || "未接入")}</li>
            </ul>
          </article>
          <article class="dynamic-card">
            <h3>最新财报口径</h3>
            <ul class="source-meta-list">
              <li><strong>财年：</strong>${snapshot ? `FY${escapeHtml(String(snapshot.fiscal_year))}` : "-"}</li>
              <li><strong>快照来源：</strong>${escapeHtml(snapshot?.source || "-")}</li>
              <li><strong>复核状态：</strong>${escapeHtml(snapshot?.status || "-")}${snapshot?.reviewed_at ? ` · ${escapeHtml(formatDateTime(snapshot.reviewed_at))}` : ""}</li>
            </ul>
          </article>
          <article class="dynamic-card">
            <h3>当前折现模板</h3>
            <ul class="source-meta-list">
              <li><strong>模板：</strong>${escapeHtml(policy?.policy_id || "-")}</li>
              <li><strong>折现率 R：</strong>${policy ? escapeHtml(formatRatioPct(policy.r, 2)) : "-"}</li>
              <li><strong>长期增长 g2：</strong>${policy ? escapeHtml(formatRatioPct(policy.g_terminal, 2)) : "-"}</li>
            </ul>
          </article>
        </div>
      </div>
    `;
  }

  function buildOpportunityReasonItems(profile, opportunityRow, dcfData) {
    const items = [];
    const valuation = dcfData?.overview?.latest_valuation || null;

    if (opportunityRow?.best_group) {
      items.push(`当前最匹配方法论：${opportunityRow.best_group}`);
    }
    if (opportunityRow?.best_reason) {
      items.push(`机会打分摘要：${opportunityRow.best_reason}`);
    }
    if (opportunityRow?.reason) {
      items.push(`组内理由：${opportunityRow.reason}`);
    }

    if (valuation) {
      items.push(
        `当前安全边际 ${formatSignedPct(valuation.mos_base, 2)}，中性估值 ${formatNum(valuation.iv_base, 2)}，现价 ${formatNum(valuation.price, 2)}。`
      );

      const impliedGrowth = toNumber(valuation.implied_growth_at_price);
      const baseGrowth = toNumber(valuation.g_base);
      const impliedGap =
        impliedGrowth === null || baseGrowth === null ? null : impliedGrowth - baseGrowth;
      if (impliedGap !== null) {
        const gapDirection = impliedGap < 0 ? "低于" : impliedGap > 0 ? "高于" : "接近";
        items.push(
          `当前价隐含增长 ${formatSignedPct(valuation.implied_growth_at_price, 2)}，${gapDirection}设定中性增长 ${formatSignedPct(valuation.g_base, 2)}。`
        );
      }

      items.push(
        `如果回到 20% / 40% 提醒价，对应隐含增长分别是 ${formatSignedPct(valuation.implied_growth_at_20, 2)} / ${formatSignedPct(valuation.implied_growth_at_40, 2)}。`
      );
    }

    if (!items.length) {
      items.push("当前仅有基础画像，机会原因待随着估值主链路或机会池命中后补齐。");
    }

    return items;
  }

  function buildTraceSummaryItems(traceRow) {
    if (!traceRow) return [];
    const groups = Array.isArray(traceRow.groups) ? [...traceRow.groups] : [];
    groups.sort((a, b) => Number(b.weighted_contribution || 0) - Number(a.weighted_contribution || 0));
    const topGroup = groups[0] || null;
    const metrics = traceRow.metrics_market_norm || {};

    return [
      {
        title: "综合分",
        value: formatNum(traceRow.composite_score, 2),
      },
      {
        title: "市场与层级",
        value: `${traceRow.market || "-"} · ${topGroup ? TIER_LABELS[topGroup.tier] || topGroup.tier || "-" : "待补"}`,
      },
      {
        title: "最强方法组",
        value: topGroup?.group_name || topGroup?.group_id || "待补",
      },
      {
        title: "市场内分位",
        value: `${formatNum((Number(metrics.margin_of_safety) || 0) * 100, 1)} / ${formatNum((Number(metrics.quality) || 0) * 100, 1)} / ${formatNum((Number(metrics.growth) || 0) * 100, 1)}`,
      },
    ];
  }

  function renderMethodTraceHtml(traceRow) {
    if (!traceRow) {
      return `
        <article class="trace-block empty-card">
          <h3>方法轨迹明细</h3>
          <p class="muted">当前口径未找到该股票的分组轨迹数据。页面已预留模块，等这只股票进入方法轨迹输出集后会自动补齐。</p>
        </article>
      `;
    }

    const groups = Array.isArray(traceRow.groups) ? [...traceRow.groups] : [];
    groups.sort((a, b) => Number(b.weighted_contribution || 0) - Number(a.weighted_contribution || 0));

    const summaryHtml = buildTraceSummaryItems(traceRow)
      .map(
        (item) => `
          <article class="trace-summary-item">
            <h4>${escapeHtml(item.title)}</h4>
            <p>${escapeHtml(item.value)}</p>
          </article>
        `
      )
      .join("");

    const body = groups
      .map((item, idx) => {
        const hardPass = item.hard_pass ? "通过" : "未通过";
        const softRules = (item.soft_penalties || [])
          .filter((row) => row && row.triggered)
          .map((row) => row.rule)
          .join(" / ");
        return `
          <tr>
            <td>${idx + 1}</td>
            <td><a class="detail-link" href="./method.html?group_id=${encodeURIComponent(item.group_id || "")}" target="_blank" rel="noreferrer">${escapeHtml(item.group_name || item.group_id || "-")}</a></td>
            <td>${escapeHtml(TIER_LABELS[item.tier] || item.tier || "-")}</td>
            <td>${escapeHtml(hardPass)}</td>
            <td>${escapeHtml(formatNum(item.base_score, 2))}</td>
            <td>${escapeHtml(formatNum(item.adjusted_score, 2))}</td>
            <td>${escapeHtml(formatNum(item.weighted_contribution, 2))}</td>
            <td>${escapeHtml((item.hard_fail_reasons || []).join(" / ") || "-")}</td>
            <td>${escapeHtml(softRules || "-")}</td>
          </tr>
        `;
      })
      .join("");

    return `
      <article class="trace-block">
        <h3>方法轨迹明细</h3>
        <div class="trace-summary-grid">${summaryHtml}</div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>方法论分组</th>
                <th>层级</th>
                <th>硬筛</th>
                <th>基础分</th>
                <th>调整后分</th>
                <th>加权贡献</th>
                <th>硬筛失败原因</th>
                <th>软惩罚命中</th>
              </tr>
            </thead>
            <tbody>${body || `<tr><td colspan="9">暂无轨迹数据</td></tr>`}</tbody>
          </table>
        </div>
      </article>
    `;
  }

  function renderThesisPanel(profile, opportunityRow, traceRow, dcfData) {
    const reasonItems = buildOpportunityReasonItems(profile, opportunityRow, dcfData)
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");

    const groups = Array.isArray(traceRow?.groups) ? [...traceRow.groups] : [];
    groups.sort((a, b) => Number(b.weighted_contribution || 0) - Number(a.weighted_contribution || 0));
    const topGroup = groups[0] || null;
    const valuation = dcfData?.overview?.latest_valuation || null;

    qs("#stock-thesis-panel").innerHTML = `
      <div class="panel-head">
        <h2>机会原因 / 方法轨迹</h2>
        <p>先把这只股票现在为什么值得继续看说清楚，再回到方法体系里看它是怎么过筛的。</p>
      </div>

      <div class="thesis-grid">
        <article class="thesis-card">
          <h3>机会原因</h3>
          <ul class="bullet-list">${reasonItems}</ul>
        </article>
        <article class="thesis-card">
          <h3>当前定位</h3>
          <ul class="source-meta-list">
            <li><strong>市场：</strong>${escapeHtml(profile.market || inferMarketFromTicker(profile.ticker || profile.symbol))}</li>
            <li><strong>当前最匹配方法：</strong>${escapeHtml(opportunityRow?.best_group || topGroup?.group_name || topGroup?.group_id || "待补")}</li>
            <li><strong>当前层级：</strong>${escapeHtml(topGroup ? TIER_LABELS[topGroup.tier] || topGroup.tier || "-" : "待补")}</li>
            <li><strong>估值锚：</strong>${valuation ? `${escapeHtml(formatSignedPct(valuation.mos_base, 2))} MOS_FV` : "待补"}</li>
          </ul>
        </article>
        <article class="thesis-card">
          <h3>方法轨迹摘要</h3>
          <ul class="source-meta-list">
            <li><strong>综合分：</strong>${escapeHtml(formatNum(traceRow?.composite_score, 2))}</li>
            <li><strong>方法组数量：</strong>${escapeHtml(String(groups.length || 0))}</li>
            <li><strong>顶部贡献组：</strong>${escapeHtml(topGroup?.group_name || topGroup?.group_id || "待补")}</li>
            <li><strong>当前状态：</strong>${groups.length ? "已进入方法轨迹输出" : "尚未进入方法轨迹输出集"}</li>
          </ul>
        </article>
      </div>

      <div class="opportunity-detail">
        ${renderMethodTraceHtml(traceRow)}
      </div>
    `;
  }

  function renderSourcesPanel(profile, opportunityRow, dcfData) {
    const overview = dcfData?.overview || {};
    const valuation = overview.latest_valuation || null;
    const snapshot = overview.latest_snapshot || null;
    const policy = overview.policy || null;
    const noteFields = parseNoteFields(opportunityRow?.note || profile.note || "");
    const confidence = explainConfidence(profile.intro_data_confidence || "unknown");
    const boundaryItems = [];

    if (resolvePriceChangePct(profile, dcfData?.quote) === null) {
      boundaryItems.push("日内涨跌幅尚未接入当前股票详情的数据合同。");
    }
    if (!snapshot) {
      boundaryItems.push("最新财报快照未联动成功时，页面会回退到静态画像层。");
    }
    if (!valuation) {
      boundaryItems.push("DCF 主估值不可用时，只展示 fallback 估值与公司画像，不伪造结果。");
    }

    qs("#stock-sources-panel").innerHTML = `
      <div class="panel-head">
        <h2>来源与口径</h2>
        <p>最后统一交代“数据从哪里来、按什么口径算、目前哪些字段还没完全接上”。</p>
      </div>

      <div class="source-columns">
        <article class="source-card-lite">
          <h3>公司画像来源</h3>
          ${renderSourcesHtml(profile.intro_sources)}
          <p class="section-subnote">披露期 ${escapeHtml(profile.intro_fiscal_period || "待补齐")} · 置信度 ${escapeHtml(confidence.label)}</p>
        </article>

        <article class="source-card-lite">
          <h3>估值口径</h3>
          <ul class="source-meta-list">
            <li><strong>DCF symbol：</strong>${escapeHtml(resolveDcfSymbol(profile, profile.symbol || profile.ticker) || "-")}</li>
            <li><strong>估值主链路：</strong>${escapeHtml(dcfData?.base || "未接通")}${dcfData?.refreshed ? " · refresh=true" : ""}</li>
            <li><strong>折现模板：</strong>${escapeHtml(policy?.policy_id || "-")} · R ${policy ? escapeHtml(formatRatioPct(policy.r, 2)) : "-"} · g2 ${policy ? escapeHtml(formatRatioPct(policy.g_terminal, 2)) : "-"}</li>
            <li><strong>财报快照：</strong>${snapshot ? `FY${escapeHtml(String(snapshot.fiscal_year))} · ${escapeHtml(snapshot.source || "-")} · ${escapeHtml(snapshot.status || "-")}` : "未拿到快照"}</li>
            <li><strong>估值刷新：</strong>${valuation?.calculated_at ? escapeHtml(formatDateTime(valuation.calculated_at)) : "-"}</li>
            <li><strong>Fair Value 来源：</strong>${escapeHtml(noteFields.fairValueSource || opportunityRow?.valuation_source || profile.source || "-")}</li>
          </ul>
        </article>

        <article class="source-card-lite">
          <h3>当前边界</h3>
          <ul class="source-meta-list">
            ${(boundaryItems.length
              ? boundaryItems.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
              : "<li>当前核心字段已接通，未发现额外边界说明。</li>")}
            <li><a class="detail-link" href="./data-info.html">查看完整数据口径页</a></li>
          </ul>
        </article>
      </div>
    `;
  }

  async function bootstrap() {
    const params = getParams();
    const ticker = params.ticker;
    if (!ticker) {
      renderNotFound("");
      return;
    }

    const pack = ["sample", "real", "real3"].includes(params.pack) ? params.pack : "real3";

    const [stockData, primaryOpportunityText, fallbackOpportunityText, primaryTraceData, fallbackTraceData] = await Promise.all([
      fetchJson(FILES.stockProfiles),
      fetchText(FILES.opportunities[pack]),
      pack === "real3" ? Promise.resolve(null) : fetchText(FILES.opportunities.real3),
      fetchJson(FILES.traces[pack]),
      pack === "real3" ? Promise.resolve(null) : fetchJson(FILES.traces.real3),
    ]);

    const opportunityRows = parseCsv(primaryOpportunityText || fallbackOpportunityText || "");
    const opportunityMap = new Map();
    opportunityRows.forEach((row) => {
      registerLookup(opportunityMap, row, [row.ticker, row.symbol, row.dcf_symbol]);
    });

    const profilesRaw = stockData?.profiles || {};
    const profileMap = new Map();
    Object.entries(profilesRaw).forEach(([key, value]) => {
      registerLookup(profileMap, value, [key, value?.ticker, value?.symbol, value?.dcf_symbol, value?.yf_ticker]);
    });

    const opportunityRow = findMappedRow(opportunityMap, ticker);
    const baseProfile = findMappedRow(profileMap, ticker);
    const profile = enrichProfile(baseProfile, ticker, opportunityRow);
    if (!profile) {
      renderNotFound(ticker);
      return;
    }

    const traceRows = Array.isArray(primaryTraceData?.rows)
      ? primaryTraceData.rows
      : Array.isArray(fallbackTraceData?.rows)
        ? fallbackTraceData.rows
        : [];
    const traceMap = new Map();
    traceRows.forEach((row) => {
      registerLookup(traceMap, row, [row?.ticker, row?.symbol, row?.dcf_symbol]);
    });
    const traceRow = findMappedRow(traceMap, ticker);

    const dcfSymbol = resolveDcfSymbol(profile, ticker);
    const dcfData = await fetchDcfOverview(dcfSymbol, params.dcfBase);

    renderCorePanel(profile, dcfData);
    renderValuationPanel(profile, opportunityRow, dcfData);
    renderBusinessPanel(profile, dcfData);
    renderThesisPanel(profile, opportunityRow, traceRow, dcfData);
    renderSourcesPanel(profile, opportunityRow, dcfData);
  }

  bootstrap();
})();
