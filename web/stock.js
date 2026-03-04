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

  function getParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      ticker: (params.get("ticker") || "").trim().toUpperCase(),
      pack: (params.get("pack") || "real3").trim(),
    };
  }

  function formatNum(value, digits = 2) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "-";
    return n.toFixed(digits);
  }

  function formatPct(value, digits = 2) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "-";
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(digits)}%`;
  }

  function toNumber(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function canonicalTicker(raw) {
    const ticker = String(raw || "").trim().toUpperCase();
    if (!ticker) return "";
    const hkMatch = ticker.match(/^(\d{1,5})\.HK$/);
    if (hkMatch) {
      return `${hkMatch[1].padStart(5, "0")}.HK`;
    }
    return ticker;
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
    const qualityScore = toNumber(opportunityRow.quality_score);
    const growthScore = toNumber(opportunityRow.growth_score);
    const momentumScore = toNumber(opportunityRow.momentum_score);
    const catalystScore = toNumber(opportunityRow.catalyst_score);
    const riskScore = toNumber(opportunityRow.risk_score);
    const certaintyScore = toNumber(opportunityRow.certainty_score);

    return {
      price_to_fair_value: p2fv,
      fair_value: fairValue,
      target_mean_price: targetMeanPrice,
      margin_of_safety_fv_pct: p2fv === null ? null : (1 - p2fv) * 100,
      quality_score: qualityScore,
      growth_score: growthScore,
      momentum_score: momentumScore,
      catalyst_score: catalystScore,
      risk_score: riskScore,
      certainty_score: certaintyScore,
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
      ticker,
      name: displayName,
      name_cn: displayName,
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
      source: "opportunities.real_3markets.csv fallback",
      valuation_real3: valuation,
      valuation_real: valuation,
      note: opportunityRow.note || "",
    };
  }

  function enrichProfile(baseProfile, ticker, opportunityRow) {
    if (!baseProfile) return buildFallbackProfile(ticker, opportunityRow);
    const profile = { ...baseProfile };
    profile.ticker = ticker;
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

  function renderTrace(traceRow) {
    const panel = qs("#stock-trace-panel");
    if (!panel) return;
    if (!traceRow) {
      panel.innerHTML = `
        <div class="panel-head">
          <h2>方法论决策轨迹</h2>
          <p>当前口径未找到该股票的分组轨迹数据。</p>
        </div>
      `;
      return;
    }

    const metrics = traceRow.metrics_market_norm || {};
    const groups = Array.isArray(traceRow.groups) ? traceRow.groups : [];
    groups.sort((a, b) => Number(b.weighted_contribution || 0) - Number(a.weighted_contribution || 0));

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

    panel.innerHTML = `
      <div class="panel-head">
        <h2>方法论决策轨迹</h2>
        <p>展示该股票在全部方法论分组中的通过/淘汰原因与最终层级。</p>
      </div>
      <div class="detail-grid">
        <article class="detail-item">
          <h4>综合分</h4>
          <p>${escapeHtml(formatNum(traceRow.composite_score, 2))}</p>
        </article>
        <article class="detail-item">
          <h4>市场</h4>
          <p>${escapeHtml(traceRow.market || "-")}</p>
        </article>
        <article class="detail-item">
          <h4>市场内分位（MOS/质量/成长）</h4>
          <p>${escapeHtml(
            `${formatNum((Number(metrics.margin_of_safety) || 0) * 100, 1)} / ${formatNum(
              (Number(metrics.quality) || 0) * 100,
              1
            )} / ${formatNum((Number(metrics.growth) || 0) * 100, 1)}`
          )}</p>
        </article>
        <article class="detail-item">
          <h4>市场内分位（趋势/催化/风控）</h4>
          <p>${escapeHtml(
            `${formatNum((Number(metrics.momentum) || 0) * 100, 1)} / ${formatNum(
              (Number(metrics.catalyst) || 0) * 100,
              1
            )} / ${formatNum((Number(metrics.risk_control) || 0) * 100, 1)}`
          )}</p>
        </article>
      </div>
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
    `;
  }

  function renderTraceLoading() {
    const panel = qs("#stock-trace-panel");
    if (!panel) return;
    panel.innerHTML = `
      <div class="panel-head">
        <h2>方法论决策轨迹</h2>
        <p>轨迹数据加载中...</p>
      </div>
    `;
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
    return `<ul>${items}</ul>`;
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

  function explainConfidence(rawValue) {
    const key = String(rawValue || "unknown").trim();
    const label = CONFIDENCE_LABELS[key] || key || CONFIDENCE_LABELS.unknown;
    const estimated = key.includes("estimated");
    const note = estimated
      ? "当前包含估算成分，优先用于研究与跟踪，不建议直接作为交易定量输入。"
      : "当前以公司披露口径为主，适合做方法论验证与对比。";
    return { key, label, estimated, note };
  }

  function renderStock(profile, meta) {
    const displayName = profile.name_cn && profile.name_cn !== profile.name
      ? `${profile.name_cn} / ${profile.name}`
      : profile.name;
    qs("#stock-title").textContent = `${displayName} (${profile.ticker})`;
    qs("#stock-subtitle").textContent = `${profile.market || inferMarketFromTicker(profile.ticker)} | ${
      profile.sector || "-"
    } | ${profile.industry || "-"} | 数据源：${
      profile.source || "-"
    }`;

    qs("#stock-price-panel").innerHTML = `
      <div class="panel-head">
        <h2>当前股价</h2>
        <p>展示当前价格、币种与更新日期。</p>
      </div>
      <div class="detail-grid">
        <article class="detail-item">
          <h4>现价</h4>
          <p>${escapeHtml(formatNum(profile.current_price, 4))}</p>
        </article>
        <article class="detail-item">
          <h4>币种</h4>
          <p>${escapeHtml(profile.currency || "-")}</p>
        </article>
        <article class="detail-item">
          <h4>价格日期</h4>
          <p>${escapeHtml(profile.price_as_of || "-")}</p>
        </article>
        <article class="detail-item">
          <h4>官网</h4>
          <p>${
            profile.website
              ? `<a href="${escapeHtml(profile.website)}" target="_blank" rel="noreferrer">${escapeHtml(
                  profile.website
                )}</a>`
              : "-"
          }</p>
        </article>
      </div>
    `;

    const businessIntro =
      profile.business_intro_zh ||
      "当前未接入该股票的中文公司介绍模板（已保留价格、估值与方法论轨迹数据）。";
    const productsIntro =
      profile.products_intro_zh ||
      "当前未接入该股票的中文产品结构模板，建议优先补齐年报分部收入、客户结构和竞争力要点。";
    const introFiscalPeriod = profile.intro_fiscal_period || "待补齐";
    const confidence = explainConfidence(profile.intro_data_confidence || "unknown");
    const keyCustomers = profile.key_customers_zh || "待补齐";
    const coreCompetitiveness = profile.core_competitiveness_zh || "待补齐";
    const revenueShareNote = profile.revenue_share_note_zh || "待补齐";
    const introSources = renderSourcesHtml(profile.intro_sources);

    qs("#stock-business-panel").innerHTML = `
      <div class="panel-head">
        <h2>公司与产品介绍</h2>
        <p>以下为中文口径：公司做什么、卖什么、收入来自哪里、客户是谁、竞争力在哪。</p>
      </div>
      <div class="detail-grid">
        <article class="detail-item">
          <h4>公司介绍（中文）</h4>
          <p>${escapeHtml(businessIntro)}</p>
        </article>
        <article class="detail-item">
          <h4>披露期与置信度</h4>
          <p>${escapeHtml(`披露期：${introFiscalPeriod}｜置信度：${confidence.label}`)}</p>
        </article>
        <article class="detail-item">
          <h4>公司主要客户</h4>
          <p>${escapeHtml(keyCustomers)}</p>
        </article>
        <article class="detail-item">
          <h4>公司核心竞争力</h4>
          <p>${escapeHtml(coreCompetitiveness)}</p>
        </article>
        <article class="detail-item">
          <h4>收入占比口径说明</h4>
          <p>${escapeHtml(revenueShareNote)}</p>
        </article>
        <article class="detail-item">
          <h4>补充文字说明</h4>
          <p>${escapeHtml(productsIntro)}</p>
        </article>
      </div>
      <div class="opportunity-detail">
        <h3>产品结构明细（中文）</h3>
        ${renderProductBreakdown(profile)}
      </div>
      <div class="opportunity-detail">
        <h3>口径风险提示</h3>
        <p class="muted">${escapeHtml(confidence.note)}</p>
      </div>
      <div class="opportunity-detail detail-ref">
        <h3>数据来源</h3>
        ${introSources}
      </div>
    `;

    const val = profile.valuation_real3 || profile.valuation_real || {};
    qs("#stock-valuation-panel").innerHTML = `
      <div class="panel-head">
        <h2>估值情况</h2>
        <p>${escapeHtml(meta.non_realtime_disclaimer || "市场数据口径，存在短延迟。")}</p>
      </div>
      <div class="detail-grid">
        <article class="detail-item">
          <h4>Price/Fair Value</h4>
          <p>${escapeHtml(formatNum(val.price_to_fair_value, 4))}</p>
        </article>
        <article class="detail-item">
          <h4>安全边际(FV口径)</h4>
          <p>${escapeHtml(formatPct(val.margin_of_safety_fv_pct, 2))}</p>
        </article>
        <article class="detail-item">
          <h4>目标价（分析师均值）</h4>
          <p>${escapeHtml(formatNum(profile.target_mean_price, 2))}</p>
        </article>
        <article class="detail-item">
          <h4>Trailing PE / Forward PE</h4>
          <p>${escapeHtml(formatNum(profile.trailing_pe, 2))} / ${escapeHtml(formatNum(profile.forward_pe, 2))}</p>
        </article>
        <article class="detail-item">
          <h4>Price to Book</h4>
          <p>${escapeHtml(formatNum(profile.price_to_book, 2))}</p>
        </article>
        <article class="detail-item">
          <h4>EV/EBITDA</h4>
          <p>${escapeHtml(formatNum(profile.enterprise_to_ebitda, 2))}</p>
        </article>
        <article class="detail-item">
          <h4>市值</h4>
          <p>${escapeHtml(formatNum(profile.market_cap, 0))}</p>
        </article>
        <article class="detail-item">
          <h4>因子分（质量/成长/趋势）</h4>
          <p>${escapeHtml(formatNum(val.quality_score, 1))} / ${escapeHtml(formatNum(val.growth_score, 1))} / ${escapeHtml(
      formatNum(val.momentum_score, 1)
    )}</p>
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

    const [stockData, primaryOpportunityText] = await Promise.all([
      fetchJson(FILES.stockProfiles),
      fetchText(FILES.opportunities[pack]),
    ]);
    const opportunityText = primaryOpportunityText || (await fetchText(FILES.opportunities.real3));
    const opportunityRows = parseCsv(opportunityText);
    const opportunityMap = {};
    opportunityRows.forEach((row) => {
      const key = canonicalTicker(row.ticker);
      if (key) opportunityMap[key] = row;
    });

    const profilesRaw = stockData?.profiles || {};
    const profileMap = {};
    Object.entries(profilesRaw).forEach(([key, value]) => {
      const canonical = canonicalTicker(key || value?.ticker);
      if (!canonical) return;
      profileMap[canonical] = value;
    });

    const canonical = canonicalTicker(ticker);
    const opportunityRow = opportunityMap[canonical] || null;
    const baseProfile = profileMap[canonical] || null;
    const profile = enrichProfile(baseProfile, ticker, opportunityRow);
    if (!profile) {
      renderNotFound(ticker);
      return;
    }
    renderStock(profile, stockData || {});
    renderTraceLoading();

    const primaryTraceData = await fetchJson(FILES.traces[pack]);
    const traceData = primaryTraceData || (await fetchJson(FILES.traces.real3));
    const traceRows = Array.isArray(traceData?.rows) ? traceData.rows : [];
    const traceRow =
      traceRows.find((item) => canonicalTicker(item?.ticker) === canonical) ||
      traceRows.find((item) => canonicalTicker(item?.ticker) === canonicalTicker(ticker)) ||
      null;
    renderTrace(traceRow);
  }

  bootstrap();
})();
