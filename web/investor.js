(function () {
  const DATA_PATHS = {
    profiles: "../data/investor_profiles.json",
    methodologyV3: "../data/investor_methodology_v3.json",
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

  function getQueryId() {
    const params = new URLSearchParams(window.location.search);
    return params.get("id");
  }

  async function fetchJson(path) {
    const res = await fetch(path);
    if (!res.ok) return null;
    return res.json();
  }

  async function loadData() {
    const [profiles, methodologyV3] = await Promise.all([
      fetchJson(DATA_PATHS.profiles),
      fetchJson(DATA_PATHS.methodologyV3),
    ]);
    if (!profiles) {
      throw new Error(`failed to load ${DATA_PATHS.profiles}`);
    }
    return { profiles, methodologyV3 };
  }

  function formatAnnualized(item) {
    if (item.calibrated_return_pct !== null && item.calibrated_return_pct !== undefined) {
      return `${item.calibrated_return_pct}%（可审计口径）`;
    }
    if (item.annualized_return_proxy_pct !== null && item.annualized_return_proxy_pct !== undefined) {
      return `~${item.annualized_return_proxy_pct}%（13F代理，非审计）`;
    }
    return "未披露";
  }

  function getV3Row(methodologyV3, investorId) {
    const rows = methodologyV3?.investors || [];
    return rows.find((item) => item.id === investorId) || null;
  }

  function renderHero(item, v3Row) {
    const avatarEl = qs("#profile-avatar");
    const fallbackEl = qs("#profile-avatar-fallback");
    const fallbackText = (item.name_cn || item.name_en || "?").slice(0, 1);
    fallbackEl.textContent = fallbackText;

    if (item.avatar_url) {
      avatarEl.src = item.avatar_url;
      avatarEl.style.display = "block";
      fallbackEl.style.display = "none";
      avatarEl.onerror = () => {
        avatarEl.style.display = "none";
        fallbackEl.style.display = "inline-flex";
      };
    } else {
      avatarEl.style.display = "none";
      fallbackEl.style.display = "inline-flex";
    }
    qs("#profile-name").textContent = `${item.name_cn || ""} / ${item.name_en || ""}`;
    qs("#profile-intro").textContent = item.personal_intro || "未提供个人介绍";

    const methodLabel = v3Row?.primary_family_name || item.methodology_bucket || "-";
    const trackLabel = v3Row?.track_name || "未分轨";
    const investabilityLabel =
      (v3Row?.investability && (INVESTABILITY_LABELS[v3Row.investability] || v3Row.investability)) || "-";
    const executionTags = Array.isArray(v3Row?.execution_tags) ? v3Row.execution_tags.join(" / ") : "-";
    const badges = [
      `类型：${ROLE_LABELS[item.role_type] || item.role_type || "投资人"}`,
      `可信度：${item.confidence || "-"}`,
      `方法论V3：${methodLabel}`,
      `分轨：${trackLabel}`,
      `可投性：${investabilityLabel}`,
      `执行标签：${executionTags}`,
      `风格：${item.style || "-"}`,
    ];
    qs("#profile-badges").innerHTML = badges.map((text) => `<span class="pill">${escapeHtml(text)}</span>`).join("");
  }

  function renderMetrics(item, v3Row) {
    const disclosure = item.disclosure_entity;
    const disclosureText = disclosure
      ? `${disclosure.entity_name || "-"}（CIK ${disclosure.cik || "-"}）`
      : "未配置披露实体";
    const disclosureStatus = disclosure
      ? disclosure.status === "ok"
        ? `已抓取：${disclosure.report_date || "-"} ${disclosure.accession || ""}`.trim()
        : disclosure.status === "not_applicable_13f"
          ? "该主体不适用13F实体披露（采用议员交易披露口径）"
          : disclosure.status === "insider_disclosure"
            ? "该主体采用管理层持股披露口径（非13F）"
            : "未抓取到最新披露"
      : "-";
    const disclosureLink =
      disclosure && disclosure.detail_url
        ? `<a class="detail-link" target="_blank" rel="noreferrer" href="${escapeHtml(
            disclosure.detail_url
          )}">查看披露详情</a>`
        : "";

    const annualizedBasis =
      item.calibrated_return_pct !== null && item.calibrated_return_pct !== undefined
        ? item.return_basis || "-"
        : item.annualized_return_proxy_basis || item.return_basis || "-";
    const annualizedPeriod =
      item.calibrated_return_pct !== null && item.calibrated_return_pct !== undefined
        ? item.period || "-"
        : item.annualized_return_proxy_period || item.period || "-";
    const proxyNote = item.annualized_return_proxy_note || "-";
    const secondaryFamilies = Array.isArray(v3Row?.secondary_family_names)
      ? v3Row.secondary_family_names.filter(Boolean).join(" / ")
      : "";
    const executionTags = Array.isArray(v3Row?.execution_tags) ? v3Row.execution_tags.join(" / ") : "-";
    const disclosureTags = Array.isArray(v3Row?.disclosure_tags) ? v3Row.disclosure_tags.join(" / ") : "-";
    const methodTrack = v3Row?.track_name || "未分轨";
    const methodFamily = v3Row?.primary_family_name || item.methodology_bucket || "-";
    const investability =
      (v3Row?.investability && (INVESTABILITY_LABELS[v3Row.investability] || v3Row.investability)) || "-";
    const mappingConfidence = v3Row?.mapping_confidence || "-";
    const mappingNote = v3Row?.mapping_note || "-";

    qs("#profile-metrics").innerHTML = `
      <div class="panel-head">
        <h2>基础信息</h2>
        <p>统一展示：收益口径、统计区间、披露实体、投资思路、持仓说明</p>
      </div>
      <div class="detail-grid">
        <article class="detail-item">
          <h4>年化收益</h4>
          <p>${escapeHtml(formatAnnualized(item))}</p>
        </article>
        <article class="detail-item">
          <h4>收益口径</h4>
          <p>${escapeHtml(annualizedBasis)}</p>
        </article>
        <article class="detail-item">
          <h4>业绩补充</h4>
          <p>${escapeHtml(item.performance_summary || "-")}</p>
        </article>
        <article class="detail-item">
          <h4>统计区间</h4>
          <p>${escapeHtml(annualizedPeriod)}</p>
        </article>
        <article class="detail-item">
          <h4>代理收益说明</h4>
          <p>${escapeHtml(proxyNote)}</p>
        </article>
        <article class="detail-item">
          <h4>投资思路</h4>
          <p>${escapeHtml(item.thesis || "-")}</p>
        </article>
        <article class="detail-item">
          <h4>方法论V3</h4>
          <p>主家族：${escapeHtml(methodFamily)}</p>
          <p>分轨：${escapeHtml(methodTrack)} / ${escapeHtml(investability)}</p>
          <p>次级家族：${escapeHtml(secondaryFamilies || "-")}</p>
          <p class="muted">映射可信度：${escapeHtml(mappingConfidence)}</p>
          <p class="muted">${escapeHtml(mappingNote)}</p>
        </article>
        <article class="detail-item">
          <h4>披露实体</h4>
          <p>${escapeHtml(disclosureText)}</p>
          <p class="muted">${escapeHtml(disclosureStatus)}</p>
          <p class="muted">${disclosureLink}</p>
        </article>
      </div>
      <article class="detail-item" style="margin-top: 10px;">
        <h4>持仓说明</h4>
        <p>${escapeHtml(item.holdings_note || "-")}</p>
        <p class="muted">执行标签：${escapeHtml(executionTags)}</p>
        <p class="muted">披露标签：${escapeHtml(disclosureTags)}</p>
        <p class="muted">富途对照：${escapeHtml(item.futu_alignment_status || "-")} / ${escapeHtml(
          item.futu_alignment_note || "-"
        )}</p>
        <p class="muted">全接口量化（主指标）：命中 ${escapeHtml(
          String(item?.interface_quant?.priced_asset_count ?? 0)
        )}/${escapeHtml(String(item?.interface_quant?.eligible_asset_count ?? 0))} 个可报价持仓；资产覆盖 ${escapeHtml(
          item?.interface_quant?.priced_asset_coverage_pct === null ||
            item?.interface_quant?.priced_asset_coverage_pct === undefined
            ? "-"
            : `${item.interface_quant.priced_asset_coverage_pct}%`
        )}；权重覆盖 ${escapeHtml(
          item?.interface_quant?.priced_weight_coverage_pct === null ||
            item?.interface_quant?.priced_weight_coverage_pct === undefined
            ? "-"
            : `${item.interface_quant.priced_weight_coverage_pct}%`
        )}</p>
        <p class="muted">OpenD量化（诊断）：命中 ${escapeHtml(
          String(item?.opend_quant?.priced_asset_count ?? 0)
        )} 个持仓；权重覆盖 ${escapeHtml(
          item?.opend_quant?.priced_weight_coverage_pct === null ||
            item?.opend_quant?.priced_weight_coverage_pct === undefined
            ? "-"
            : `${item.opend_quant.priced_weight_coverage_pct}%`
        )}</p>
      </article>
    `;
  }

  function renderHoldings(item) {
    const rows = Array.isArray(item.representative_holdings_with_weight)
      ? item.representative_holdings_with_weight
      : [];
    const tableRows = rows
      .map((row) => {
        const ticker = row.ticker || "-";
        const assetCn = row.asset_cn || "-";
        const price = row.price_text || "-";
        const currency = row.price_currency || "-";
        const weight = row.weight_text || "-";
        const updated = row.holding_updated_at || row.weight_as_of || "-";
        const change = row.position_change_text || "-";
        const note = row.position_change_note || row.weight_note || "-";
        const priceDate = row.price_as_of ? ` (${row.price_as_of})` : "";
        return `
          <tr>
            <td>${escapeHtml(row.asset || "-")}</td>
            <td>${escapeHtml(assetCn)}</td>
            <td>${escapeHtml(ticker)}</td>
            <td>${escapeHtml(price)}${escapeHtml(priceDate)}</td>
            <td>${escapeHtml(currency)}</td>
            <td>${escapeHtml(weight)}</td>
            <td>${escapeHtml(updated)}</td>
            <td>${escapeHtml(change)}</td>
            <td>${escapeHtml(note)}</td>
          </tr>
        `;
      })
      .join("");

    qs("#holdings-table-wrap").innerHTML = `
      <table>
        <thead>
          <tr>
            <th>资产</th>
            <th>中文名称</th>
            <th>代码</th>
            <th>最新价格</th>
            <th>币种</th>
            <th>持仓占比</th>
            <th>持仓更新时间</th>
            <th>持仓变动比例</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows || `<tr><td colspan="9">暂无持仓数据</td></tr>`}
        </tbody>
      </table>
    `;
  }

  function renderSources(item, rootMeta) {
    const refs = Array.isArray(item.source_refs) ? item.source_refs : [];
    const sourceLegend = rootMeta?.source_legend || {};
    const list = refs
      .map((ref) => {
        const desc = sourceLegend[ref] || ref;
        return `<li><strong>${escapeHtml(ref)}：</strong>${escapeHtml(desc)}</li>`;
      })
      .join("");

    qs("#profile-sources").innerHTML = `
      <div class="panel-head">
        <h2>来源与口径</h2>
        <p>用于判断数据是可审计、披露跟踪，还是代表性资料。</p>
      </div>
      <div class="detail-grid">
        <article class="detail-item">
          <h4>引用来源</h4>
          <ul>${list || "<li>-</li>"}</ul>
        </article>
        <article class="detail-item">
          <h4>全局说明</h4>
          <ul>
            <li>${escapeHtml(rootMeta?.coverage_note || "-")}</li>
            <li>${escapeHtml(rootMeta?.holdings_field_note || "-")}</li>
            <li>${escapeHtml(rootMeta?.price_data_source || "-")}</li>
          </ul>
        </article>
      </div>
    `;
  }

  function renderNotFound(investorId) {
    document.body.innerHTML = `
      <main class="detail-page">
        <section class="panel">
          <h1>未找到投资者</h1>
          <p class="muted">id=${escapeHtml(investorId || "空")} 不存在。</p>
          <p><a href="./index.html">返回总览页</a></p>
        </section>
      </main>
    `;
  }

  async function bootstrap() {
    const investorId = getQueryId();
    if (!investorId) {
      renderNotFound("");
      return;
    }

    try {
      const { profiles, methodologyV3 } = await loadData();
      const investor = (profiles.investors || []).find((item) => item.id === investorId);
      if (!investor) {
        renderNotFound(investorId);
        return;
      }
      const v3Row = getV3Row(methodologyV3, investorId);
      renderHero(investor, v3Row);
      renderMetrics(investor, v3Row);
      renderHoldings(investor);
      renderSources(investor, profiles);
    } catch (error) {
      renderNotFound(investorId);
      // eslint-disable-next-line no-console
      console.error(error);
    }
  }

  bootstrap();
})();
