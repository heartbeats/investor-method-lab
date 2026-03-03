(function () {
  const FILES = {
    investorProfiles: "../data/investor_profiles.json",
    methodologyV3: "../data/investor_methodology_v3.json",
    taxonomyV3: "../data/methodology_taxonomy_v3.json",
    stockProfiles: "../data/stock_profiles.json",
    framework: "../data/top20_methodology_framework.json",
    metaReal3: "../docs/opportunities_real_data_meta_3markets.json",
    metaReal: "../docs/opportunities_real_data_meta.json",
    packs: {
      sample: {
        groupLegacy: "../output/top20_methodology_top5_by_group.csv",
        groupTiered: "../output/top20_methodology_top10_by_group_tiered.csv",
        trace: "../output/method_decision_trace.json",
        label: "样本口径（非真实数据）",
        dataKind: "sample",
      },
      real: {
        groupLegacy: "../output/top20_methodology_top5_by_group_real.csv",
        groupTiered: "../output/top20_methodology_top10_by_group_tiered_real.csv",
        trace: "../output/method_decision_trace_real.json",
        label: "实时口径（US）",
        dataKind: "real",
      },
      real3: {
        groupLegacy: "../output/top20_methodology_top5_by_group_real_3markets.csv",
        groupTiered: "../output/top20_methodology_top10_by_group_tiered_real_3markets.csv",
        trace: "../output/method_decision_trace_real_3markets.json",
        label: "实时口径（A/HK/US）",
        dataKind: "real",
      },
    },
  };

  const FAMILY_TO_GROUP_IDS = {
    quality_value_compounding: ["value_quality_compound"],
    deep_value_distress: ["deep_value_recovery", "credit_cycle"],
    garp_growth: ["garp_growth"],
    thematic_innovation_growth: ["garp_growth"],
    event_driven_special_situations: ["event_driven_activist"],
    macro_discretionary: ["macro_regime"],
    trend_following: ["trend_following"],
    systematic_value_factors: ["systematic_quant"],
    quant_stat_arb: ["systematic_quant"],
    equity_long_short_trading: ["event_driven_activist", "systematic_quant"],
    industry_specialist_value: ["industry_compounder"],
  };

  const TRACK_LABELS = {
    investment_method: "投资方法主体",
    disclosure_observation: "披露跟踪主体",
  };

  const INVESTABILITY_LABELS = {
    stock_selection_eligible: "可用于选股",
    observation_only: "仅观察",
  };

  const TIER_LABELS = {
    core: "核心池",
    watch: "观察池",
    tactical: "战术池",
  };

  const state = {
    selectedPack: "real3",
    selectedTier: "core",
    selectedMarket: "ALL",
    packRows: {
      sample: [],
      real: [],
      real3: [],
    },
    traceMap: {
      sample: {},
      real: {},
      real3: {},
    },
    stockProfiles: {},
    methodContext: null,
    investorRows: [],
    metaReal3: null,
    metaReal: null,
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

  function inferMarketFromTicker(ticker) {
    const value = String(ticker || "").trim().toUpperCase();
    if (value.endsWith(".SS") || value.endsWith(".SZ")) return "A";
    if (value.endsWith(".HK")) return "HK";
    return "US";
  }

  function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      familyId: params.get("family_id") || "",
      groupId: params.get("group_id") || "",
    };
  }

  function getMetaByPack() {
    if (state.selectedPack === "real3") return state.metaReal3;
    if (state.selectedPack === "real") return state.metaReal;
    return null;
  }

  function parseMethodContext(params, taxonomyV3, framework) {
    if (params.familyId && taxonomyV3) {
      const families = Array.isArray(taxonomyV3.families) ? taxonomyV3.families : [];
      const tracks = Array.isArray(taxonomyV3.tracks) ? taxonomyV3.tracks : [];
      const family = families.find((item) => item.id === params.familyId);
      if (family) {
        const track = tracks.find((item) => item.id === family.track);
        return {
          mode: "family",
          id: family.id,
          name: family.name,
          coreQuestion: family.core_question || "-",
          trackId: family.track || "",
          trackName: track?.name || TRACK_LABELS[family.track] || family.track || "-",
          useForStockSelection: track?.use_for_stock_selection === true,
          groupIds: FAMILY_TO_GROUP_IDS[family.id] || [],
        };
      }
    }

    if (params.groupId && framework && Array.isArray(framework.groups)) {
      const group = framework.groups.find((item) => item.id === params.groupId);
      if (group) {
        return {
          mode: "group",
          id: group.id,
          name: group.name,
          coreQuestion: group.core_question || "-",
          trackId: "investment_method",
          trackName: "投资方法主体",
          useForStockSelection: true,
          groupIds: [group.id],
        };
      }
    }
    return null;
  }

  function renderNotFound(message) {
    document.body.innerHTML = `
      <main class="detail-page">
        <section class="panel">
          <h1>未找到方法论</h1>
          <p class="muted">${escapeHtml(message || "参数无效或数据未加载。")}</p>
          <p><a href="./index.html">返回总览页</a></p>
        </section>
      </main>
    `;
  }

  function renderHero(context, investorRows) {
    qs("#method-title").textContent = `${context.name || "-"} 方法详情`;
    qs("#method-subtitle").textContent = context.coreQuestion || "-";
    const badges = [
      `分轨：${context.trackName || "-"}`,
      `可投性：${context.useForStockSelection ? "可用于选股" : "仅观察"}`,
      `覆盖主体：${investorRows.length}`,
      `机会映射组：${context.groupIds.length ? context.groupIds.join(" / ") : "无直接映射"}`,
    ];
    qs("#method-badges").innerHTML = badges.map((text) => `<span class="pill">${escapeHtml(text)}</span>`).join("");
  }

  function renderInvestors(rows) {
    const panel = qs("#method-investor-panel");
    const body = rows
      .map((item, idx) => {
        const investorHref = `./investor.html?id=${encodeURIComponent(item.id || "")}`;
        const investability = INVESTABILITY_LABELS[item.investability] || item.investability || "-";
        return `
          <tr>
            <td>${idx + 1}</td>
            <td><a class="detail-link" href="${investorHref}">${escapeHtml(item.name_cn || item.name_en || item.id || "-")}</a></td>
            <td>${escapeHtml(item.role_type || "-")}</td>
            <td>${escapeHtml(item.primary_family_name || "-")}</td>
            <td>${escapeHtml(investability)}</td>
            <td>${escapeHtml((item.execution_tags || []).join(" / ") || "-")}</td>
            <td>${escapeHtml((item.disclosure_tags || []).join(" / ") || "-")}</td>
          </tr>
        `;
      })
      .join("");

    panel.innerHTML = `
      <div class="panel-head">
        <h2>该方法对应主体</h2>
        <p>主体按 V3 方法论映射归类，可点击进入投资者详情。</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>主体</th>
              <th>类型</th>
              <th>主家族</th>
              <th>可投性</th>
              <th>执行标签</th>
              <th>披露标签</th>
            </tr>
          </thead>
          <tbody>${body || `<tr><td colspan="7">暂无主体</td></tr>`}</tbody>
        </table>
      </div>
    `;
  }

  function renderOpportunityTable(rows) {
    const tableBody = rows
      .map((row, idx) => {
        const ticker = row.ticker || "-";
        const stockHref = row.ticker
          ? `./stock.html?ticker=${encodeURIComponent(row.ticker)}&pack=${encodeURIComponent(state.selectedPack)}`
          : "#";
        const stock = state.stockProfiles[ticker] || null;
        const nameCn = stock?.name_cn;
        const displayName = nameCn && nameCn !== row.name ? `${nameCn} / ${row.name || "-"}` : row.name || "-";
        const tier = row.tier || "core";
        const hardPassLabel = String(row.hard_pass).toLowerCase() === "true" ? "通过" : "未通过";
        return `
          <tr>
            <td>${idx + 1}</td>
            <td>${escapeHtml(row.group_name || "-")}</td>
            <td>${escapeHtml(TIER_LABELS[tier] || tier)}</td>
            <td>${escapeHtml(row.group_rank || "-")}</td>
            <td>${row.ticker ? `<a class="detail-link" href="${stockHref}" target="_blank" rel="noreferrer">${escapeHtml(ticker)}</a>` : "-"}</td>
            <td>${row.ticker ? `<a class="detail-link" href="${stockHref}" target="_blank" rel="noreferrer">${escapeHtml(displayName)}</a>` : escapeHtml(displayName)}</td>
            <td>${escapeHtml(row.market || inferMarketFromTicker(row.ticker || ""))}</td>
            <td>${escapeHtml(row.sector || "-")}</td>
            <td>${escapeHtml(row.group_score || "-")}</td>
            <td>${escapeHtml(row.penalty_multiplier || "-")}</td>
            <td>${escapeHtml(hardPassLabel)}</td>
            <td>${escapeHtml(row.reason || row.hard_fail_reasons || "-")}</td>
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
              <th>机会组</th>
              <th>层级</th>
              <th>组内排名</th>
              <th>代码</th>
              <th>公司</th>
              <th>市场</th>
              <th>行业</th>
              <th>组内分</th>
              <th>惩罚乘数</th>
              <th>硬筛</th>
              <th>解释</th>
            </tr>
          </thead>
          <tbody>${tableBody || `<tr><td colspan="12">暂无映射机会</td></tr>`}</tbody>
        </table>
      </div>
    `;
  }

  function renderTraceSummary(rows, groupIds) {
    const panel = qs("#method-trace-summary");
    if (!panel) return;
    const totals = {
      core: 0,
      watch: 0,
      tactical: 0,
    };
    rows.forEach((row) => {
      const tier = row.tier || "core";
      if (totals[tier] !== undefined) totals[tier] += 1;
    });
    const groupText = groupIds.length ? groupIds.join(" / ") : "无";
    panel.innerHTML = `
      <div class="detail-grid">
        <article class="detail-item">
          <h4>映射分组</h4>
          <p>${escapeHtml(groupText)}</p>
        </article>
        <article class="detail-item">
          <h4>核心池命中</h4>
          <p>${totals.core}</p>
        </article>
        <article class="detail-item">
          <h4>观察池命中</h4>
          <p>${totals.watch}</p>
        </article>
        <article class="detail-item">
          <h4>战术池命中</h4>
          <p>${totals.tactical}</p>
        </article>
      </div>
    `;
  }

  function getFilteredRowsForMethod() {
    const allRows = state.packRows[state.selectedPack] || [];
    const groupIds = state.methodContext?.groupIds || [];
    let rows = allRows.filter((row) => groupIds.includes(row.group_id));

    if (state.selectedTier !== "ALL") {
      rows = rows.filter((row) => (row.tier || "core") === state.selectedTier);
    }
    if (state.selectedMarket !== "ALL") {
      rows = rows.filter((row) => (row.market || inferMarketFromTicker(row.ticker || "")) === state.selectedMarket);
    }
    rows.sort((a, b) => {
      const scoreA = Number(a.group_score || 0);
      const scoreB = Number(b.group_score || 0);
      return scoreB - scoreA;
    });
    return rows;
  }

  function renderOpportunities() {
    const meta = getMetaByPack();
    const groupIds = state.methodContext?.groupIds || [];
    const rows = getFilteredRowsForMethod();
    const allRowsForSummary = (state.packRows[state.selectedPack] || []).filter((row) =>
      groupIds.includes(row.group_id)
    );

    const metaText = meta
      ? `${FILES.packs[state.selectedPack].label}；来源：${meta.source || "-"}；行情日期：${
          Array.isArray(meta.as_of_dates) ? meta.as_of_dates.join(", ") : "-"
        }`
      : `${FILES.packs[state.selectedPack].label}；样本口径仅用于流程演示`;

    qs("#method-opportunity-meta").textContent = metaText;
    renderTraceSummary(allRowsForSummary, groupIds);
    if (!groupIds.length) {
      qs("#method-opportunity-content").innerHTML = `<article class="detail-card"><p class="muted">该方法属于“观察类”或当前未配置机会组映射，暂无直接机会池结果。</p></article>`;
      return;
    }
    qs("#method-opportunity-content").innerHTML = renderOpportunityTable(rows);
  }

  function bindEvents() {
    const packSelect = qs("#method-pack-select");
    const tierSelect = qs("#method-tier-select");
    const marketSelect = qs("#method-market-select");
    if (packSelect) {
      packSelect.addEventListener("change", (event) => {
        state.selectedPack = event.target.value || "real3";
        renderOpportunities();
      });
    }
    if (tierSelect) {
      tierSelect.addEventListener("change", (event) => {
        state.selectedTier = event.target.value || "core";
        renderOpportunities();
      });
    }
    if (marketSelect) {
      marketSelect.addEventListener("change", (event) => {
        state.selectedMarket = event.target.value || "ALL";
        renderOpportunities();
      });
    }
  }

  async function loadPackRows() {
    const modes = Object.keys(FILES.packs);
    for (const mode of modes) {
      const tieredText = await fetchText(FILES.packs[mode].groupTiered);
      const legacyText = await fetchText(FILES.packs[mode].groupLegacy);
      const rows = parseCsv(tieredText || legacyText || "");
      state.packRows[mode] = rows.map((row) => {
        const item = { ...row };
        item.tier = item.tier || "core";
        item.market = item.market || inferMarketFromTicker(item.ticker || "");
        return item;
      });

      const tracePayload = await fetchJson(FILES.packs[mode].trace);
      const map = {};
      const traceRows = Array.isArray(tracePayload?.rows) ? tracePayload.rows : [];
      traceRows.forEach((item) => {
        const ticker = String(item?.ticker || "").toUpperCase();
        if (!ticker) return;
        map[ticker] = item;
      });
      state.traceMap[mode] = map;
    }
  }

  async function bootstrap() {
    const params = getQueryParams();
    const [profiles, methodologyV3, taxonomyV3, stockProfiles, framework, metaReal3, metaReal] = await Promise.all([
      fetchJson(FILES.investorProfiles),
      fetchJson(FILES.methodologyV3),
      fetchJson(FILES.taxonomyV3),
      fetchJson(FILES.stockProfiles),
      fetchJson(FILES.framework),
      fetchJson(FILES.metaReal3),
      fetchJson(FILES.metaReal),
    ]);

    if (!profiles || !methodologyV3) {
      renderNotFound("核心数据缺失：investor_profiles 或 investor_methodology_v3 未加载。");
      return;
    }

    state.stockProfiles = stockProfiles?.profiles || {};
    state.metaReal3 = metaReal3;
    state.metaReal = metaReal;
    state.methodContext = parseMethodContext(params, taxonomyV3, framework);
    if (!state.methodContext) {
      renderNotFound("请通过首页点击方法论卡片进入，或检查 family_id/group_id 参数。");
      return;
    }

    let rows = [];
    if (state.methodContext.mode === "family") {
      rows = (methodologyV3.investors || []).filter((item) => item.primary_family_id === state.methodContext.id);
    } else if (state.methodContext.mode === "group" && framework && Array.isArray(framework.groups)) {
      const group = framework.groups.find((item) => item.id === state.methodContext.id);
      const bucketMatches = Array.isArray(group?.bucket_matches) ? group.bucket_matches : [];
      const candidateIds = (profiles.investors || [])
        .filter((item) => bucketMatches.includes(item.methodology_bucket))
        .map((item) => item.id);
      const byId = {};
      (methodologyV3.investors || []).forEach((item) => {
        byId[item.id] = item;
      });
      rows = candidateIds.map((id) => byId[id]).filter(Boolean);
    }
    state.investorRows = rows;

    await loadPackRows();
    renderHero(state.methodContext, rows);
    renderInvestors(rows);
    renderOpportunities();
    bindEvents();
  }

  bootstrap();
})();
