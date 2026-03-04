(function () {
  const FILES = {
    investorProfiles: "../data/investor_profiles.json",
    methodologyV3: "../data/investor_methodology_v3.json",
    taxonomyV3: "../data/methodology_taxonomy_v3.json",
    investorsVerified: "../data/top20_global_investors_verified_ab.json",
    investorsVerifiedA: "../data/top20_global_investors_verified_a_only.json",
    investorsCalibrated: "../data/top20_global_investors_10y_plus_calibrated.json",
    framework: "../data/top20_methodology_framework.json",
    methodologies: "../data/methodologies.json",
    metaReal3: "../docs/opportunities_real_data_meta_3markets.json",
    metaReal: "../docs/opportunities_real_data_meta.json",
    stockProfiles: "../data/stock_profiles.json",
    dataSourceCatalog: "../data/data_source_catalog.json",
    futuAlignmentReport: "../data/futu_alignment_report.json",
    packs: {
      sample: {
        top: "../output/top20_first_batch_opportunities.csv",
        diversified: "../output/top20_diversified_opportunities.csv",
        group: "../output/top20_methodology_top5_by_group.csv",
        input: "../data/opportunities.sample.csv",
        label: "样本口径（非真实数据）",
        dataKind: "sample",
      },
      real: {
        top: "../output/top20_first_batch_opportunities_real.csv",
        diversified: "../output/top20_diversified_opportunities_real.csv",
        group: "../output/top20_methodology_top5_by_group_real.csv",
        input: "../data/opportunities.real.csv",
        label: "实时口径（US）",
        dataKind: "real",
      },
      real3: {
        top: "../output/top20_first_batch_opportunities_real_3markets.csv",
        diversified: "../output/top20_diversified_opportunities_real_3markets.csv",
        group: "../output/top20_methodology_top5_by_group_real_3markets.csv",
        input: "../data/opportunities.real_3markets.csv",
        label: "实时口径（A/HK/US）",
        dataKind: "real",
      },
    },
  };

  const state = {
    selectedPack: "real3",
    selectedView: "top",
    selectedOpportunityKey: null,
    investorSearch: "",
    confidenceFilter: "ALL",
    methodologyFilter: "ALL",
    datasets: {
      investorProfiles: null,
      methodologyV3: null,
      taxonomyV3: null,
      investorsVerified: null,
      investorsVerifiedA: null,
      investorsCalibrated: null,
      framework: null,
      methodologies: null,
      metaReal3: null,
      metaReal: null,
      stockProfiles: null,
      dataSourceCatalog: null,
      futuAlignmentReport: null,
      packs: {
        sample: null,
        real: null,
        real3: null,
      },
    },
  };

  const FACTOR_LABELS = {
    margin_of_safety: "安全边际",
    quality: "质量",
    growth: "成长",
    momentum: "趋势",
    catalyst: "催化",
    risk_control: "风控",
  };

  const ROLE_LABELS = {
    investor: "投资人",
    fund_manager: "基金经理",
    insider: "高管披露",
    politician_disclosure: "议员披露",
    public_figure: "公众人物",
  };

  const INVESTABILITY_LABELS = {
    stock_selection_eligible: "可用于选股",
    observation_only: "仅观察",
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

  function toNumber(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function formatSignedPct(decimalValue) {
    if (!Number.isFinite(decimalValue)) return "-";
    const sign = decimalValue > 0 ? "+" : "";
    return `${sign}${(decimalValue * 100).toFixed(2)}%`;
  }

  function buildHoverBadge(titleText, label = "查看说明") {
    const text = String(titleText || "").trim();
    if (!text) return "";
    return `<span class="hint-badge" title="${escapeHtml(text)}" aria-label="${escapeHtml(label)}">i</span>`;
  }

  function buildDataBasisHover(meta, asOfDates) {
    const dcfMeta = meta?.dcf_integration || {};
    const requested = dcfMeta?.dcf_base_url_requested || dcfMeta?.dcf_base_url || "-";
    const effective = dcfMeta?.dcf_base_url_effective || requested;
    const probeRows = Array.isArray(dcfMeta?.dcf_base_url_probe) ? dcfMeta.dcf_base_url_probe : [];
    const probeText = probeRows.length
      ? probeRows
          .map((item) => {
            const base = String(item?.base_url || "-");
            const status = item?.ok ? "ok" : String(item?.reason || "fail");
            return `${base}:${status}`;
          })
          .join(" | ")
      : "无";
    const coverage = toNumber(dcfMeta?.coverage_ratio);
    const coverageText = Number.isFinite(coverage) ? `${(coverage * 100).toFixed(1)}%` : "-";
    const cachePolicy = String(meta?.cache_policy || "-");
    const source = String(meta?.source || "项目数据");

    return [
      `来源=${source}`,
      `行情日期=${asOfDates || "-"}`,
      `DCF请求地址=${requested}`,
      `DCF实际地址=${effective}`,
      `DCF探测=${probeText}`,
      `DCF覆盖=${coverageText}`,
      `缓存策略=${cachePolicy}`,
    ].join("；");
  }

  function parseNoteMetrics(noteText) {
    const text = String(noteText || "");
    const closeMatch = text.match(/close=([0-9]+(?:\.[0-9]+)?)/i);
    const targetMatch = text.match(/target=([0-9]+(?:\.[0-9]+)?)/i);
    const upsideMatch = text.match(/upside=([-+]?[0-9]+(?:\.[0-9]+)?)%/i);
    const asOfMatch = text.match(/real-data@(\d{4}-\d{2}-\d{2})/i);

    return {
      close: closeMatch ? Number(closeMatch[1]) : null,
      target: targetMatch ? Number(targetMatch[1]) : null,
      upsidePct: upsideMatch ? Number(upsideMatch[1]) / 100 : null,
      asOfDate: asOfMatch ? asOfMatch[1] : null,
    };
  }

  function renderFatal(title, tips) {
    const lines = (tips || []).map((line) => `<li>${escapeHtml(line)}</li>`).join("");
    document.body.innerHTML = `
      <main style="max-width:800px;margin:60px auto;padding:28px;border:1px solid #d3c8ae;border-radius:16px;background:#fffaf0;color:#2a3642;font-family:'Noto Sans SC',sans-serif;">
        <h1 style="margin:0 0 12px 0;font-size:28px;">${escapeHtml(title)}</h1>
        <p style="margin:0 0 14px 0;color:#5f6f7d;">请按下面步骤打开看板：</p>
        <ul style="margin:0;padding-left:18px;line-height:1.8;">${lines}</ul>
      </main>
    `;
  }

  async function fetchJson(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) {
        return null;
      }
      return await res.json();
    } catch (_err) {
      return null;
    }
  }

  async function fetchText(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) {
        return null;
      }
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
        if (ch === "\r" && next === "\n") {
          i += 1;
        }
        row.push(value);
        value = "";
        if (row.some((item) => item !== "")) {
          rows.push(row);
        }
        row = [];
      } else {
        value += ch;
      }
    }

    if (value.length > 0 || row.length > 0) {
      row.push(value);
      if (row.some((item) => item !== "")) {
        rows.push(row);
      }
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

  function toPct(weight) {
    const n = Number(weight) || 0;
    return `${(n * 100).toFixed(1)}%`;
  }

  function buildMethodologyWeights(group, strategyById) {
    let weights = group.custom_weights || {};
    if (!group.custom_weights && group.base_strategy_id) {
      const strategy = strategyById[group.base_strategy_id];
      if (strategy && strategy.weights) {
        weights = strategy.weights;
      }
    }

    const keys = Object.keys(FACTOR_LABELS);
    const total = keys.reduce((sum, key) => sum + Math.max(0, Number(weights[key]) || 0), 0);
    if (total <= 0) {
      return keys.reduce((acc, key) => {
        acc[key] = 1 / keys.length;
        return acc;
      }, {});
    }

    return keys.reduce((acc, key) => {
      acc[key] = (Math.max(0, Number(weights[key]) || 0)) / total;
      return acc;
    }, {});
  }

  function mapInvestorsById(list) {
    const map = {};
    (list || []).forEach((item) => {
      map[item.id] = item;
    });
    return map;
  }

  function getMethodologyV3Map() {
    const rows = state.datasets.methodologyV3?.investors || [];
    return mapInvestorsById(rows);
  }

  function getV3Row(item) {
    if (!item || !item.id) return null;
    return getMethodologyV3Map()[item.id] || null;
  }

  function getMethodologyLabel(item) {
    const v3 = getV3Row(item);
    if (v3 && v3.primary_family_name) return v3.primary_family_name;
    return item?.methodology_bucket || "-";
  }

  function getMethodologyTrackLabel(item) {
    const v3 = getV3Row(item);
    if (v3 && v3.track_name) return v3.track_name;
    return "未分轨";
  }

  function getInvestabilityLabel(item) {
    const v3 = getV3Row(item);
    if (v3 && v3.investability) {
      return INVESTABILITY_LABELS[v3.investability] || v3.investability;
    }
    return "-";
  }

  function renderSummary() {
    const profiles = state.datasets.investorProfiles;
    const methodologyV3 = state.datasets.methodologyV3;
    const taxonomyV3 = state.datasets.taxonomyV3;
    const verified = state.datasets.investorsVerified;
    const verifiedA = state.datasets.investorsVerifiedA;
    const framework = state.datasets.framework;
    const metaReal3 = state.datasets.metaReal3;

    const profileCount = profiles?.investor_count || profiles?.investors?.length || verified?.included_count || 0;
    const aCount = (profiles?.investors || []).filter((item) => item.confidence === "A").length;
    const v3InvestmentFamilyCount = (taxonomyV3?.families || []).filter((item) => item.track === "investment_method").length;
    const legacyGroupCount = framework ? (framework.groups || []).length : null;
    const groupCount = v3InvestmentFamilyCount || legacyGroupCount || 0;

    qs("#summary-investor-count").textContent = String(profileCount || 0);
    qs("#summary-a-count").textContent = String(aCount || verifiedA?.included_count || 0);
    qs("#summary-group-count").textContent = String(groupCount || 0);
    qs("#summary-universe-count").textContent = metaReal3 ? String(metaReal3.universe_size || 0) : "-";

    const asOf = profiles?.as_of_date || verified?.as_of_date || "未知";
    const marketDate = Array.isArray(metaReal3?.as_of_dates) ? metaReal3.as_of_dates.join(", ") : "未知";
    const v3Date = methodologyV3?.generated_at_utc ? String(methodologyV3.generated_at_utc).slice(0, 10) : "未加载";
    qs("#hero-subtitle").textContent = `投资人数据日期：${asOf}；方法论口径：V3（${v3Date}）；三市场行情日期：${marketDate}`;
  }

  function getInvestorUniverse() {
    const profiles = state.datasets.investorProfiles;
    if (profiles && Array.isArray(profiles.investors)) return profiles.investors;
    const verified = state.datasets.investorsVerified;
    return Array.isArray(verified?.investors) ? verified.investors : [];
  }

  function getHoldingsWithWeight(item) {
    const weighted = Array.isArray(item?.representative_holdings_with_weight)
      ? item.representative_holdings_with_weight
      : [];

    if (weighted.length) {
      return weighted.map((row) => {
        const asset = row?.asset || "";
        const assetCn = row?.asset_cn || "";
        const weightText = row?.weight_text || "未披露";
        const weightNote = row?.weight_note || "";
        const asOf = row?.weight_as_of || "";
        const assetLabel = assetCn && assetCn !== asset ? `${assetCn}/${asset}` : asset;
        return {
          asset,
          assetCn,
          weightText,
          weightNote,
          asOf,
          display: asOf ? `${assetLabel}（${weightText}，${asOf}）` : `${assetLabel}（${weightText}）`,
          searchable: `${asset} ${assetCn} ${weightText} ${weightNote} ${asOf}`,
        };
      });
    }

    return (item?.representative_holdings || []).map((asset) => ({
      asset,
      weightText: "",
      asOf: "",
      display: asset,
      searchable: asset,
    }));
  }

  function getFilteredInvestors() {
    const allInvestors = getInvestorUniverse();
    if (!allInvestors.length) return [];

    const keyword = state.investorSearch.trim().toLowerCase();
    return allInvestors.filter((item) => {
      if (state.confidenceFilter !== "ALL" && item.confidence !== state.confidenceFilter) {
        return false;
      }
      if (state.methodologyFilter !== "ALL" && getMethodologyLabel(item) !== state.methodologyFilter) {
        return false;
      }
      if (!keyword) {
        return true;
      }

      const v3 = getV3Row(item);
      const executionTags = Array.isArray(v3?.execution_tags) ? v3.execution_tags.join(" ") : "";
      const disclosureTags = Array.isArray(v3?.disclosure_tags) ? v3.disclosure_tags.join(" ") : "";

      const haystack = [
        item.name_cn,
        item.name_en,
        item.style,
        getMethodologyLabel(item),
        getMethodologyTrackLabel(item),
        getInvestabilityLabel(item),
        item.personal_intro,
        executionTags,
        disclosureTags,
        ...getHoldingsWithWeight(item).map((h) => h.searchable),
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(keyword);
    });
  }

  function renderInvestorFilters() {
    const investors = getInvestorUniverse();
    const methodologySelect = qs("#methodology-filter");
    const old = state.methodologyFilter;

    const buckets = Array.from(
      new Set((investors || []).map((item) => getMethodologyLabel(item)).filter(Boolean))
    ).sort();

    methodologySelect.innerHTML = `<option value="ALL">全部</option>${buckets
      .map((bucket) => `<option value="${escapeHtml(bucket)}">${escapeHtml(bucket)}</option>`)
      .join("")}`;

    if (buckets.includes(old)) {
      methodologySelect.value = old;
    }
  }

  function renderInvestorTable() {
    const tbody = qs("#investor-table tbody");
    const list = getFilteredInvestors();

    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="10">暂无匹配数据</td></tr>`;
      return;
    }

    tbody.innerHTML = list
      .map((item) => {
        const rank = item.profile_rank || item.verified_rank || item.rank || "-";
        const annualized =
          item.calibrated_return_pct === null || item.calibrated_return_pct === undefined
            ? item.annualized_return_proxy_pct === null || item.annualized_return_proxy_pct === undefined
              ? "-"
              : `~${item.annualized_return_proxy_pct}%*`
            : `${item.calibrated_return_pct}%`;
        const roleTypeRaw = item.role_type || "investor";
        const roleType = ROLE_LABELS[roleTypeRaw] || roleTypeRaw;
        const methodologyLabel = getMethodologyLabel(item);
        const intro = String(item.personal_intro || "").trim() || "-";
        const holdings = getHoldingsWithWeight(item)
          .slice(0, 4)
          .map((h) => h.display)
          .join("、");
        const avatarHtml = item.avatar_url
          ? `<img class="avatar-sm" src="${escapeHtml(item.avatar_url)}" alt="${escapeHtml(
              item.name_cn || item.name_en || "avatar"
            )}" loading="lazy" referrerpolicy="no-referrer" />`
          : `<span class="avatar-sm avatar-fallback">${escapeHtml((item.name_cn || item.name_en || "?").slice(0, 1))}</span>`;
        return `
          <tr data-investor-id="${escapeHtml(item.id)}">
            <td>${escapeHtml(rank)}</td>
            <td>
              <div class="investor-cell">
                ${avatarHtml}
                <div>
                  <strong>${escapeHtml(item.name_cn || "")}</strong><br />
                  <span class="muted">${escapeHtml(item.name_en || "")}</span>
                </div>
              </div>
            </td>
            <td>${escapeHtml(annualized)}</td>
            <td>${escapeHtml(roleType)}</td>
            <td>${escapeHtml(item.confidence || "-")}</td>
            <td>${escapeHtml(methodologyLabel)}</td>
            <td>${escapeHtml(item.style || "-")}</td>
            <td>${escapeHtml(intro.length > 60 ? `${intro.slice(0, 60)}...` : intro)}</td>
            <td>${escapeHtml(holdings || "-")}</td>
            <td><a class="detail-link" href="./investor.html?id=${encodeURIComponent(item.id)}">查看详情</a></td>
          </tr>
        `;
      })
      .join("");

    tbody.querySelectorAll("tr[data-investor-id]").forEach((row) => {
      row.addEventListener("click", (event) => {
        if (event.target.closest("a")) return;
        const investorId = row.getAttribute("data-investor-id");
        if (!investorId) return;
        window.location.href = `./investor.html?id=${encodeURIComponent(investorId)}`;
      });
    });
  }

  function renderInvestorDetail() {
    const container = qs("#investor-detail");
    if (!container) return;
    const profilesMeta = state.datasets.investorProfiles || {};
    const coverageNote =
      profilesMeta.holdings_field_note ||
      state.datasets.investorsVerified?.holdings_weight_coverage_note ||
      "持仓字段含价格、占比、更新时间、变动比例；无披露时会标注“未披露/不适用”。";
    const annualizedNote =
      profilesMeta.annualized_return_note || "带 * 的年化值为13F代理口径（非审计净值），仅供参考。";
    const interfaceSummary = profilesMeta.interface_quant_summary || null;
    const futuRuntime = profilesMeta.futu_alignment_runtime || null;
    const opendSummary = profilesMeta.opend_quant_summary || null;
    const interfaceSummaryText = interfaceSummary
      ? `${interfaceSummary.investor_covered_count || 0}/${interfaceSummary.investor_total_count || 0} 人有报价；可报价持仓 ${
          interfaceSummary.total_priced_assets || 0
        }/${interfaceSummary.total_eligible_assets || 0}（${
          interfaceSummary.asset_coverage_pct === null || interfaceSummary.asset_coverage_pct === undefined
            ? "-"
            : `${interfaceSummary.asset_coverage_pct}%`
        }）`
      : "未记录";
    const futuRuntimeText = futuRuntime
      ? `${futuRuntime.status || "-"} / ${futuRuntime.endpoint || "-"} / ${futuRuntime.note || "-"}`
      : "未记录";
    const opendSummaryText = opendSummary
      ? `${opendSummary.investor_covered_count || 0}/${opendSummary.investor_total_count || 0} 人命中，累计 ${
          opendSummary.total_priced_assets || 0
        } 个持仓`
      : "未记录";
    container.innerHTML = `
      <h3>详情页已上线</h3>
      <p class="muted">请点击表格最右侧“查看详情”，进入投资者个人详情页。</p>
      <p class="muted">口径说明：${escapeHtml(coverageNote)}</p>
      <p class="muted">收益说明：${escapeHtml(annualizedNote)}</p>
      <p class="muted">全接口量化覆盖（主指标）：${escapeHtml(interfaceSummaryText)}</p>
      <p class="muted">富途对照运行态：${escapeHtml(futuRuntimeText)}</p>
      <p class="muted">OpenD量化覆盖（诊断）：${escapeHtml(opendSummaryText)}</p>
    `;
  }

  function renderMethodologyCards() {
    const taxonomyV3 = state.datasets.taxonomyV3;
    const methodologyV3 = state.datasets.methodologyV3;
    const container = qs("#method-grid");

    if (taxonomyV3 && methodologyV3 && Array.isArray(methodologyV3.investors)) {
      const trackById = {};
      (taxonomyV3.tracks || []).forEach((track) => {
        if (track && track.id) trackById[track.id] = track;
      });
      const profilesById = mapInvestorsById(getInvestorUniverse());

      const cards = (taxonomyV3.families || [])
        .map((family) => {
          const members = (methodologyV3.investors || []).filter((item) => item.primary_family_id === family.id);
          if (!members.length) return "";

          const track = trackById[family.track] || {};
          const useForSelection = track.use_for_stock_selection === true;
          if (!useForSelection) return "";
          const memberNames = members
            .map((member) => {
              const profile = profilesById[member.id] || {};
              return member.name_cn || profile.name_cn || member.name_en || profile.name_en || member.id;
            })
            .join("、");

          const tagCountMap = {};
          members.forEach((member) => {
            (member.execution_tags || []).forEach((tag) => {
              const key = String(tag || "");
              if (!key) return;
              tagCountMap[key] = (tagCountMap[key] || 0) + 1;
            });
          });
          const topTags = Object.entries(tagCountMap)
            .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
            .slice(0, 5)
            .map(([tag, count]) => `${tag}(${count})`)
            .join("、");

          return `
            <a class="method-link-card" href="./method.html?family_id=${encodeURIComponent(family.id)}">
            <article class="method-card">
              <div class="method-title">
                <h3>${escapeHtml(family.name || family.id || "-")}</h3>
                <p>${escapeHtml(track.name || family.track || "-")} / ${useForSelection ? "可选股" : "观察类"}</p>
              </div>
              <p class="method-question">${escapeHtml(family.core_question || "-")}</p>
              <p class="method-members"><strong>主体数量：</strong>${escapeHtml(String(members.length))}</p>
              <p class="method-members"><strong>代表主体：</strong>${escapeHtml(memberNames || "-")}</p>
              <p class="method-members"><strong>高频执行标签：</strong>${escapeHtml(topTags || "-")}</p>
            </article>
            </a>
          `;
        })
        .filter(Boolean)
        .join("");

      container.innerHTML = cards || "<p>V3 方法论数据为空。</p>";
      return;
    }

    const framework = state.datasets.framework;
    const methodologies = state.datasets.methodologies;
    const verified = state.datasets.investorsVerified;
    if (!framework || !methodologies || !verified) {
      container.innerHTML = "<p>方法论数据加载失败。</p>";
      return;
    }

    const strategyById = {};
    (methodologies.strategies || []).forEach((item) => {
      strategyById[item.id] = item;
    });

    const investors = verified.investors || [];

    container.innerHTML = (framework.groups || [])
      .map((group) => {
        const weights = buildMethodologyWeights(group, strategyById);
        const members = investors
          .filter((inv) => (group.bucket_matches || []).includes(inv.methodology_bucket))
          .map((inv) => inv.name_cn)
          .join("、");

        const weightRows = Object.keys(FACTOR_LABELS)
          .map((key) => {
            const v = Number(weights[key] || 0);
            return `
              <div class="weight-row">
                <span>${FACTOR_LABELS[key]}</span>
                <div class="bar"><span style="width:${(v * 100).toFixed(1)}%"></span></div>
                <span>${toPct(v)}</span>
              </div>
            `;
          })
          .join("");

        return `
          <a class="method-link-card" href="./method.html?group_id=${encodeURIComponent(group.id || "")}">
          <article class="method-card">
            <div class="method-title">
              <h3>${escapeHtml(group.name || "")}</h3>
              <p>${escapeHtml(group.id || "")}</p>
            </div>
            <p class="method-question">${escapeHtml(group.core_question || "-")}</p>
            <div class="weight-list">${weightRows}</div>
            <p class="method-members"><strong>代表投资人：</strong>${escapeHtml(members || "暂无")}</p>
          </article>
          </a>
        `;
      })
      .join("");
  }

  function getActiveOpportunityMeta() {
    if (state.selectedPack === "real3") return state.datasets.metaReal3;
    if (state.selectedPack === "real") return state.datasets.metaReal;
    return null;
  }

  function renderOpportunityNotice() {
    const pack = FILES.packs[state.selectedPack];
    const meta = getActiveOpportunityMeta();
    const notice = qs("#data-disclaimer");

    if (pack.dataKind === "sample") {
      notice.className = "notice warn";
      notice.textContent = "当前为样本口径（非真实数据）。仅用于流程演示，请勿据此做交易决策。";
      return;
    }

    notice.className = "notice ok";
    const asOfDates = Array.isArray(meta?.as_of_dates) ? meta.as_of_dates.join(", ") : "未知";
    const source = meta?.source || "市场数据";
    notice.textContent = `当前为真实数据驱动口径（来源：${source}；行情日期：${asOfDates}）。注意可能存在短延迟。`;
  }

  function renderOpportunityTable(rows, columns) {
    function buildStockDetailHref(ticker) {
      return `./stock.html?ticker=${encodeURIComponent(ticker)}&pack=${encodeURIComponent(state.selectedPack)}`;
    }

    const header = columns.map((c) => `<th>${escapeHtml(c.label)}</th>`).join("");
    const body = rows
      .map((row, idx) => {
        const cells = columns
          .map((c) => {
            const v = c.key === "_rank" ? idx + 1 : row[c.key];
            if (c.key === "ticker" && row.ticker) {
              return `<td><a class="detail-link" href="${buildStockDetailHref(
                row.ticker
              )}" target="_blank" rel="noreferrer">${escapeHtml(v ?? "-")}</a></td>`;
            }
            if (c.key === "name") {
              const cn = getStockNameCn(row.ticker, row.name);
              const label = cn && cn !== row.name ? `${cn} / ${row.name || "-"}` : row.name || "-";
              if (row.ticker) {
                return `<td><a class="detail-link" href="${buildStockDetailHref(
                  row.ticker
                )}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a></td>`;
              }
              return `<td>${escapeHtml(label)}</td>`;
            }
            if ((c.key === "composite_score" || c.key === "group_score") && row.ticker) {
              return `<td><a class="detail-link score-link" href="${buildStockDetailHref(
                row.ticker
              )}" target="_blank" rel="noreferrer">${escapeHtml(v ?? "-")}</a></td>`;
            }
            return `<td>${escapeHtml(v ?? "-")}</td>`;
          })
          .join("");
        const rowKey = String(row._rowKey || "");
        const selectedClass = rowKey && rowKey === state.selectedOpportunityKey ? " selected" : "";
        return `<tr data-op-row-key="${escapeHtml(rowKey)}" class="${selectedClass}">${cells}</tr>`;
      })
      .join("");

    return `
      <div class="table-wrap">
        <table>
          <thead><tr>${header}</tr></thead>
          <tbody>${body || `<tr><td colspan="${columns.length}">无数据</td></tr>`}</tbody>
        </table>
      </div>
    `;
  }

  function buildOpportunityRows(rows, viewName) {
    return (rows || []).map((row, idx) => ({
      ...row,
      _rowKey: `${state.selectedPack}:${viewName}:${row.group_id || ""}:${row.group_rank || ""}:${row.ticker || ""}:${idx}`,
    }));
  }

  function ensureOpportunitySelection(rows) {
    if (!rows.length) {
      state.selectedOpportunityKey = null;
      return;
    }
    const matched = rows.some((row) => row._rowKey === state.selectedOpportunityKey);
    if (!matched) {
      state.selectedOpportunityKey = rows[0]._rowKey;
    }
  }

  function bindOpportunityRows() {
    qs("#opportunity-content")
      .querySelectorAll("tr[data-op-row-key]")
      .forEach((row) => {
        row.addEventListener("click", (event) => {
          if (event.target.closest("a")) return;
          state.selectedOpportunityKey = row.getAttribute("data-op-row-key");
          renderOpportunityContent();
        });
      });
  }

  function getStockNameCn(ticker, fallbackName) {
    const map = state.datasets.stockProfiles?.profiles || {};
    const profile = ticker ? map[ticker] : null;
    if (profile && profile.name_cn) return profile.name_cn;
    return fallbackName || null;
  }

  function renderOpportunityDetail(selectedRow, packData, meta) {
    const container = qs("#opportunity-detail");
    if (!selectedRow) {
      container.innerHTML = `
        <h3>股票详情：安全边际对比</h3>
        <p class="muted">当前视图没有可展示数据。</p>
      `;
      return;
    }

    const inputRow = (packData?.inputMap || {})[selectedRow.ticker || ""] || null;
    const noteText = inputRow?.note || selectedRow.note || "";
    const noteMetrics = parseNoteMetrics(noteText);
    const priceToFairValue =
      toNumber(inputRow?.price_to_fair_value) ??
      (() => {
        const mosPct = toNumber(selectedRow.margin_of_safety);
        if (!Number.isFinite(mosPct)) return null;
        return 1 - mosPct / 100;
      })();

    const mosFv =
      Number.isFinite(priceToFairValue) && priceToFairValue !== null
        ? 1 - priceToFairValue
        : (() => {
            const mosPct = toNumber(selectedRow.margin_of_safety);
            return Number.isFinite(mosPct) ? mosPct / 100 : null;
          })();

    const upsideFromMos =
      Number.isFinite(mosFv) && mosFv !== null && mosFv < 1 ? mosFv / (1 - mosFv) : null;
    const upsideFromYahoo = noteMetrics.upsidePct;
    const upsideValue = upsideFromYahoo ?? upsideFromMos;

    const mosSource =
      inputRow && Number.isFinite(toNumber(inputRow.price_to_fair_value))
        ? "项目计算（price_to_fair_value -> MOS_FV）"
        : "机会包字段（margin_of_safety）";
    const upsideSource =
      Number.isFinite(upsideFromYahoo)
        ? "Yahoo/分析师目标价（note 中 target/upside）"
        : "项目换算（由 MOS_FV 推导）";

    const valuationTag = Number.isFinite(mosFv)
      ? mosFv >= 0
        ? "当前显示为低估空间"
        : "当前显示为高估幅度（负值）"
      : "估值口径数据不足";

    const externalRefs = Array.isArray(meta?.external_mos_references) ? meta.external_mos_references : [];
    const refLines = externalRefs
      .map(
        (item) =>
          `<li><strong>${escapeHtml(item.source || "-")}：</strong>${escapeHtml(item.reference || "-")} ${
            item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">链接</a>` : ""
          }</li>`
      )
      .join("");

    const sourceText = escapeHtml(meta?.source || "项目数据");
    const asOfDates = Array.isArray(meta?.as_of_dates) ? meta.as_of_dates.join(", ") : "-";
    const dataBasisHover = buildDataBasisHover(meta, asOfDates);
    const dataBasisBadge = buildHoverBadge(dataBasisHover, "数据依据说明");
    const dcfMeta = meta?.dcf_integration || {};
    const dcfRequested = dcfMeta?.dcf_base_url_requested || dcfMeta?.dcf_base_url || "-";
    const dcfEffective = dcfMeta?.dcf_base_url_effective || dcfRequested || "-";
    const dcfRouteText = dcfEffective !== dcfRequested ? `${dcfRequested} → ${dcfEffective}` : dcfEffective;
    const qualityRaw = String(inputRow?.dcf_quality_gate_status || "").trim().toLowerCase();
    const qualityScore = toNumber(inputRow?.dcf_quality_gate_score);
    const qualityIssues = String(inputRow?.dcf_quality_gate_issues || "").trim();
    const crossRaw = String(inputRow?.dcf_comps_crosscheck_status || "").trim().toLowerCase();
    const crossDeviation = toNumber(inputRow?.dcf_comps_deviation_vs_median);
    const crossSource = String(inputRow?.dcf_comps_source || "").trim();
    const qualityPenalty = toNumber(inputRow?.dcf_quality_penalty_multiplier);
    const qualityTag =
      qualityRaw === "ok" ? "通过" : qualityRaw === "caution" ? "关注" : qualityRaw === "review" ? "复核" : "未提供";
    const crossTag =
      crossRaw === "ok" ? "通过" : crossRaw === "warn" ? "偏离" : crossRaw === "unavailable" ? "缺失" : "未提供";
    const qualityClass =
      qualityRaw === "ok" ? "ok" : qualityRaw === "caution" ? "warn" : qualityRaw === "review" ? "review" : "na";
    const crossClass = crossRaw === "ok" ? "ok" : crossRaw === "warn" ? "warn" : "na";
    const qualityTip = [
      "口径：终值占比、隐含增长偏差、敏感性完整性三项检查。",
      `评分=${Number.isFinite(qualityScore) ? qualityScore.toFixed(1) : "-"}`,
      `问题=${qualityIssues || "无"}`,
      "状态含义：ok=通过，caution=关注，review=需复核。",
    ].join(" ");
    const crossTip = [
      "口径：DCF中性估值与外部中位/区间的偏离对照。",
      `偏离=${Number.isFinite(crossDeviation) ? formatSignedPct(crossDeviation) : "-"}`,
      `来源=${crossSource || "-"}`,
      "状态含义：ok=通过，warn=偏离超阈值。",
    ].join(" ");
    const qualityPenaltyText = Number.isFinite(qualityPenalty) ? qualityPenalty.toFixed(4) : "-";

    container.innerHTML = `
      <h3>${escapeHtml(selectedRow.ticker || "-")} · ${escapeHtml(selectedRow.name || "-")} · 安全边际详情</h3>
      <p class="muted">${escapeHtml(selectedRow.best_group || "未分组")} | 数据来源：${sourceText} | 行情日期：${escapeHtml(asOfDates)}</p>

      <div class="mos-compare-grid">
        <article class="mos-compare-card">
          <h4>项目主口径（FV 分母）</h4>
          <p class="metric-value ${Number.isFinite(mosFv) ? (mosFv >= 0 ? "positive" : "negative") : ""}">${formatSignedPct(mosFv)}</p>
          <p class="formula-line">公式：MOS_FV = (FV - P) / FV = 1 - P/FV</p>
          <p class="source-line"><span class="source-pill">来源</span>${escapeHtml(mosSource)}</p>
        </article>

        <article class="mos-compare-card">
          <h4>目标价口径（P 分母）</h4>
          <p class="metric-value ${Number.isFinite(upsideValue) ? (upsideValue >= 0 ? "positive" : "negative") : ""}">${formatSignedPct(upsideValue)}</p>
          <p class="formula-line">公式：UPSIDE_P = (FV - P) / P = FV/P - 1</p>
          <p class="source-line"><span class="source-pill">来源</span>${escapeHtml(upsideSource)}</p>
        </article>
      </div>

      <div class="detail-grid" style="margin-top: 10px;">
        <article class="detail-item">
          <h4>口径解释</h4>
          <p>${escapeHtml(valuationTag)}；两者差异来自分母不同（FV vs P），并非方向冲突。</p>
          <p class="muted formula-line">换算：UPSIDE_P = MOS_FV / (1 - MOS_FV)，MOS_FV = UPSIDE_P / (1 + UPSIDE_P)</p>
        </article>
        <article class="detail-item">
          <h4>本条记录解析</h4>
          <p>P(close)：${Number.isFinite(noteMetrics.close) ? noteMetrics.close.toFixed(2) : "-"}</p>
          <p>FV(target)：${Number.isFinite(noteMetrics.target) ? noteMetrics.target.toFixed(2) : "-"}</p>
          <p>P/FV：${Number.isFinite(priceToFairValue) ? Number(priceToFairValue).toFixed(4) : "-"}</p>
          <p>note 日期：${escapeHtml(noteMetrics.asOfDate || "-")}</p>
          <p>数据状态：最新 ${dataBasisBadge}</p>
          <p>DCF链路：${escapeHtml(dcfRouteText)}</p>
          <p class="weak-line">质量闸门：<span class="flag-pill ${qualityClass}" title="${escapeHtml(
      qualityTip
    )}">${escapeHtml(qualityTag)}</span></p>
          <p class="weak-line">同业校验：<span class="flag-pill ${crossClass}" title="${escapeHtml(
      crossTip
    )}">${escapeHtml(crossTag)}</span></p>
          <p class="weak-line">惩罚系数：${escapeHtml(qualityPenaltyText)}</p>
        </article>
      </div>

      <article class="detail-item detail-ref">
        <h4>外部参照（用于对比口径，不用于替代主模型）</h4>
        <ul>${refLines || "<li>-</li>"}</ul>
      </article>
    `;
  }

  function renderOpportunityContent() {
    const packData = state.datasets.packs[state.selectedPack];
    const container = qs("#opportunity-content");
    const packLabel = FILES.packs[state.selectedPack].label;
    const meta = getActiveOpportunityMeta();

    const asOfDates = Array.isArray(meta?.as_of_dates) ? meta.as_of_dates.join(", ") : "-";
    qs("#opportunity-meta").textContent = `${packLabel} | 行情日期：${asOfDates}`;
    renderOpportunityNotice();

    if (!packData) {
      container.innerHTML = "<p>机会池数据加载失败。</p>";
      renderOpportunityDetail(null, null, meta);
      return;
    }

    let allRowsWithKeys = [];

    if (state.selectedView === "top") {
      const rows = buildOpportunityRows(packData.top || [], "top");
      allRowsWithKeys = rows;
      ensureOpportunitySelection(rows);
      container.innerHTML = renderOpportunityTable(rows, [
        { key: "_rank", label: "排名" },
        { key: "ticker", label: "代码" },
        { key: "name", label: "公司" },
        { key: "sector", label: "行业" },
        { key: "composite_score", label: "组合分" },
        { key: "best_group", label: "最匹配方法论" },
        { key: "best_reason", label: "理由" },
      ]);
      bindOpportunityRows();
      const selectedRow = rows.find((row) => row._rowKey === state.selectedOpportunityKey) || null;
      renderOpportunityDetail(selectedRow, packData, meta);
      return;
    }

    if (state.selectedView === "diversified") {
      const rows = buildOpportunityRows(packData.diversified || [], "diversified");
      allRowsWithKeys = rows;
      ensureOpportunitySelection(rows);
      container.innerHTML = renderOpportunityTable(rows, [
        { key: "_rank", label: "排名" },
        { key: "ticker", label: "代码" },
        { key: "name", label: "公司" },
        { key: "sector", label: "行业" },
        { key: "composite_score", label: "组合分" },
        { key: "best_group", label: "最匹配方法论" },
      ]);
      bindOpportunityRows();
      const selectedRow = rows.find((row) => row._rowKey === state.selectedOpportunityKey) || null;
      renderOpportunityDetail(selectedRow, packData, meta);
      return;
    }

    const groupRows = packData.group || [];
    const grouped = {};
    groupRows.forEach((row) => {
      const key = row.group_name || "未分组";
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(row);
    });

    const groupedWithKeys = Object.entries(grouped).map(([name, rows]) => {
      const keyedRows = buildOpportunityRows(rows, "group");
      allRowsWithKeys.push(...keyedRows);
      return [name, keyedRows];
    });
    ensureOpportunitySelection(allRowsWithKeys);

    container.innerHTML = `<div class="group-cards">${groupedWithKeys
      .map(([name, rows]) => {
        const table = renderOpportunityTable(rows, [
          { key: "group_rank", label: "组内排名" },
          { key: "ticker", label: "代码" },
          { key: "name", label: "公司" },
          { key: "group_score", label: "组内分" },
          { key: "reason", label: "理由" },
        ]);
        return `<article class="group-card"><h3>${escapeHtml(name)}</h3>${table}</article>`;
      })
      .join("")}</div>`;

    bindOpportunityRows();
    const selectedRow = allRowsWithKeys.find((row) => row._rowKey === state.selectedOpportunityKey) || null;
    renderOpportunityDetail(selectedRow, packData, meta);
  }

  function renderMetaPanel() {
    const container = qs("#meta-content");
    const metaReal3 = state.datasets.metaReal3;
    const metaReal = state.datasets.metaReal;
    const line = [
      `A/HK/US：${metaReal3?.source || "-"} @ ${(metaReal3?.as_of_dates || []).join(", ") || "-"}`,
      `US：${metaReal?.source || "-"} @ ${(metaReal?.as_of_dates || []).join(", ") || "-"}`,
      `提示：${metaReal3?.non_realtime_disclaimer || metaReal?.non_realtime_disclaimer || "-"}`,
    ].join("；");
    container.innerHTML = `<article class="meta-card meta-card-weak"><p>${escapeHtml(line)}</p></article>`;
  }

  function renderSourcePanel() {
    const container = qs("#source-content");
    const catalog = state.datasets.dataSourceCatalog;
    if (!catalog || !Array.isArray(catalog.sources)) {
      container.innerHTML = `<article class="source-summary">数据源能力文件未加载：data/data_source_catalog.json</article>`;
      return;
    }

    const statusCounts = catalog.status_counts || {};
    const summary = `探测时间：${catalog.as_of_utc || "-"}；总源数：${catalog.source_count || 0}；状态：${Object.entries(
      statusCounts
    )
      .map(([k, v]) => `${k}=${v}`)
      .join(" / ")}`;

    const cards = catalog.sources
      .map((item) => {
        const status = String(item.status || "unknown");
        const markets = Array.isArray(item.markets) ? item.markets.join("/") : "-";
        const latency = item.latency_ms === null || item.latency_ms === undefined ? "-" : `${item.latency_ms}ms`;
        return `
          <article class="source-card">
            <div class="source-head">
              <div>
                <h3>${escapeHtml(item.name || item.id || "-")}</h3>
                <p class="muted">${escapeHtml(item.category || "-")}</p>
              </div>
              <span class="status-pill ${escapeHtml(status)}">${escapeHtml(status)}</span>
            </div>
            <div class="source-meta">
              市场：${escapeHtml(markets)}；频率：${escapeHtml(item.update_frequency || "-")}；鉴权：${escapeHtml(
          item.auth || "-"
        )}；延迟：${escapeHtml(latency)}
              <br />
              说明：${escapeHtml(item.notes || "-")}
              <br />
              探测：${escapeHtml(item.detail || "-")}
            </div>
            <p class="source-link"><a href="${escapeHtml(item.url || "#")}" target="_blank" rel="noreferrer">查看来源</a></p>
          </article>
        `;
      })
      .join("");

    container.innerHTML = `<article class="source-summary">${escapeHtml(summary)}</article>${cards}`;
  }

  function renderFutuAuditPanel() {
    const container = qs("#futu-audit-content");
    const report = state.datasets.futuAlignmentReport;
    if (!report || !Array.isArray(report.investors)) {
      container.innerHTML = `<article class="source-summary">富途对账报告未加载：data/futu_alignment_report.json</article>`;
      return;
    }

    const s = report.summary || {};
    const summaryLine = `重点投资人 ${s.focus_investor_count || 0} 位；持仓行 ${s.total_holdings || 0}；可报价持仓 ${
      s.total_any_source_priced_hits || 0
    }/${s.total_quote_eligible_hits || 0}（${
      s.all_interface_asset_coverage_pct === null || s.all_interface_asset_coverage_pct === undefined
        ? "-"
        : `${s.all_interface_asset_coverage_pct}%`
    }）；OpenD应命中 ${s.total_expected_opend_hits || 0}；OpenD实际命中 ${s.total_actual_opend_hits || 0}；OpenD命中率 ${
      s.overall_expected_hit_rate_pct === null || s.overall_expected_hit_rate_pct === undefined
        ? "-"
        : `${s.overall_expected_hit_rate_pct}%`
    }；权限受限行 ${s.total_permission_blocked_rows || 0}`;

    const rows = report.investors
      .map((item) => {
        const missCount = Array.isArray(item.missing_expected_rows) ? item.missing_expected_rows.length : 0;
        const blockedCount = Array.isArray(item.permission_blocked_rows) ? item.permission_blocked_rows.length : 0;
        const hitRate =
          item.expected_hit_rate_pct === null || item.expected_hit_rate_pct === undefined
            ? "-"
            : `${item.expected_hit_rate_pct}%`;
        const interfaceAssetCoverage =
          item.all_interface_asset_coverage_pct === null || item.all_interface_asset_coverage_pct === undefined
            ? "-"
            : `${item.all_interface_asset_coverage_pct}%`;
        const interfaceWeightCoverage =
          item.disclosed_weight_any_source_coverage_pct === null ||
          item.disclosed_weight_any_source_coverage_pct === undefined
            ? "-"
            : `${item.disclosed_weight_any_source_coverage_pct}%`;
        const weightCoverage =
          item.disclosed_weight_opend_coverage_pct === null || item.disclosed_weight_opend_coverage_pct === undefined
            ? "-"
            : `${item.disclosed_weight_opend_coverage_pct}%`;
        return `
          <tr>
            <td>${escapeHtml(item.name_cn || item.id || "-")}</td>
            <td>${escapeHtml(String(item.holdings_total || 0))}</td>
            <td>${escapeHtml(`${item.any_source_priced_hits || 0}/${item.quote_eligible_hits || 0}`)}</td>
            <td>${escapeHtml(interfaceAssetCoverage)}</td>
            <td>${escapeHtml(interfaceWeightCoverage)}</td>
            <td>${escapeHtml(String(item.expected_opend_hits || 0))}</td>
            <td>${escapeHtml(String(item.actual_opend_hits || 0))}</td>
            <td>${escapeHtml(hitRate)}</td>
            <td>${escapeHtml(weightCoverage)}</td>
            <td>${escapeHtml(String(blockedCount))}</td>
            <td>${escapeHtml(String(missCount))}</td>
          </tr>
        `;
      })
      .join("");

    container.innerHTML = `
      <article class="source-summary">富途对账摘要：${escapeHtml(summaryLine)}</article>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>投资人</th>
              <th>持仓行</th>
              <th>全接口报价</th>
              <th>全接口持仓覆盖率</th>
              <th>全接口权重覆盖率</th>
              <th>应命中OpenD</th>
              <th>实际命中OpenD</th>
              <th>OpenD命中率</th>
              <th>OpenD权重覆盖率</th>
              <th>权限受限行</th>
              <th>待排查行</th>
            </tr>
          </thead>
          <tbody>
            ${rows || `<tr><td colspan="11">暂无对账结果</td></tr>`}
          </tbody>
        </table>
      </div>
    `;
  }

  function bindEvents() {
    const confidenceFilter = qs("#confidence-filter");
    if (confidenceFilter) {
      confidenceFilter.addEventListener("change", (event) => {
        state.confidenceFilter = event.target.value;
        renderInvestorTable();
      });
    }

    const methodologyFilter = qs("#methodology-filter");
    if (methodologyFilter) {
      methodologyFilter.addEventListener("change", (event) => {
        state.methodologyFilter = event.target.value;
        renderInvestorTable();
      });
    }

    const investorSearch = qs("#investor-search");
    if (investorSearch) {
      investorSearch.addEventListener("input", (event) => {
        state.investorSearch = event.target.value || "";
        renderInvestorTable();
      });
    }

    const packSelect = qs("#pack-select");
    if (packSelect) {
      packSelect.addEventListener("change", (event) => {
        state.selectedPack = event.target.value;
        state.selectedOpportunityKey = null;
        renderOpportunityContent();
        renderMetaPanel();
      });
    }

    const viewSwitch = qs("#view-switch");
    if (viewSwitch) {
      viewSwitch.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-view]");
        if (!button) return;
        state.selectedView = button.getAttribute("data-view");
        state.selectedOpportunityKey = null;
        viewSwitch
          .querySelectorAll(".switch-btn")
          .forEach((btn) => btn.classList.toggle("active", btn === button));
        renderOpportunityContent();
      });
    }
  }

  async function loadPackData() {
    const modes = Object.keys(FILES.packs);
    for (const mode of modes) {
      const conf = FILES.packs[mode];
      const [topText, diversifiedText, groupText, inputText] = await Promise.all([
        fetchText(conf.top),
        fetchText(conf.diversified),
        fetchText(conf.group),
        fetchText(conf.input),
      ]);

      const inputRows = parseCsv(inputText);
      const inputMap = {};
      inputRows.forEach((row) => {
        if (row.ticker) inputMap[row.ticker] = row;
      });

      state.datasets.packs[mode] = {
        top: parseCsv(topText),
        diversified: parseCsv(diversifiedText),
        group: parseCsv(groupText),
        inputRows,
        inputMap,
      };
    }
  }

  async function bootstrap() {
    if (window.location.protocol === "file:") {
      renderFatal("检测到 file:// 直开，浏览器会拦截本地数据读取", [
        "进入项目目录：cd /home/afu/projects/investor-method-lab",
        "执行启动脚本：bash scripts/run_dashboard.sh",
        "浏览器访问：http://127.0.0.1:8090/web/",
      ]);
      return;
    }

    const [
      investorProfiles,
      methodologyV3,
      taxonomyV3,
      investorsVerified,
      investorsVerifiedA,
      investorsCalibrated,
      framework,
      methodologies,
      metaReal3,
      metaReal,
      stockProfiles,
      dataSourceCatalog,
      futuAlignmentReport,
    ] =
      await Promise.all([
        fetchJson(FILES.investorProfiles),
        fetchJson(FILES.methodologyV3),
        fetchJson(FILES.taxonomyV3),
        fetchJson(FILES.investorsVerified),
        fetchJson(FILES.investorsVerifiedA),
        fetchJson(FILES.investorsCalibrated),
        fetchJson(FILES.framework),
        fetchJson(FILES.methodologies),
        fetchJson(FILES.metaReal3),
        fetchJson(FILES.metaReal),
        fetchJson(FILES.stockProfiles),
        fetchJson(FILES.dataSourceCatalog),
        fetchJson(FILES.futuAlignmentReport),
      ]);

    state.datasets.investorProfiles = investorProfiles;
    state.datasets.methodologyV3 = methodologyV3;
    state.datasets.taxonomyV3 = taxonomyV3;
    state.datasets.investorsVerified = investorsVerified;
    state.datasets.investorsVerifiedA = investorsVerifiedA;
    state.datasets.investorsCalibrated = investorsCalibrated;
    state.datasets.framework = framework;
    state.datasets.methodologies = methodologies;
    state.datasets.metaReal3 = metaReal3;
    state.datasets.metaReal = metaReal;
    state.datasets.stockProfiles = stockProfiles;
    state.datasets.dataSourceCatalog = dataSourceCatalog;
    state.datasets.futuAlignmentReport = futuAlignmentReport;

    const hasV3Methodology = Boolean(methodologyV3 && taxonomyV3);
    const hasLegacyMethodology = Boolean(framework && methodologies);
    if ((!investorProfiles && !investorsVerified) || (!hasV3Methodology && !hasLegacyMethodology)) {
      renderFatal("核心数据加载失败", [
        "请确认你通过本地 HTTP 服务访问，而不是直接双击 HTML 文件",
        "在项目目录执行：bash scripts/run_dashboard.sh",
        "若仍失败，检查文件是否存在：data/investor_profiles.json 与 data/investor_methodology_v3.json",
      ]);
      return;
    }

    renderSummary();
    renderInvestorFilters();
    renderInvestorTable();
    renderMethodologyCards();
    if (qs("#opportunity-content")) {
      await loadPackData();
      renderOpportunityContent();
    }
    if (qs("#meta-content")) renderMetaPanel();
    if (qs("#source-content")) renderSourcePanel();
    if (qs("#futu-audit-content")) renderFutuAuditPanel();
    bindEvents();
  }

  bootstrap();
})();
