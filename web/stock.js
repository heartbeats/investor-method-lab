(function () {
  const DATA_PATH = "../data/stock_profiles.json";

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

  function getTicker() {
    const params = new URLSearchParams(window.location.search);
    return (params.get("ticker") || "").trim().toUpperCase();
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

  async function loadData() {
    const res = await fetch(DATA_PATH);
    if (!res.ok) throw new Error(`failed to load ${DATA_PATH}`);
    return res.json();
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

  function renderStock(profile, meta) {
    const displayName = profile.name_cn && profile.name_cn !== profile.name
      ? `${profile.name_cn} / ${profile.name}`
      : profile.name;
    qs("#stock-title").textContent = `${displayName} (${profile.ticker})`;
    qs("#stock-subtitle").textContent = `${profile.sector || "-"} | ${profile.industry || "-"} | 数据源：${
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
          <p>${profile.website ? `<a href="${escapeHtml(profile.website)}" target="_blank" rel="noreferrer">${escapeHtml(profile.website)}</a>` : "-"}</p>
        </article>
      </div>
    `;

    qs("#stock-business-panel").innerHTML = `
      <div class="panel-head">
        <h2>公司与产品介绍</h2>
        <p>由公开业务描述自动归纳，供快速理解公司做什么。</p>
      </div>
      <div class="detail-grid">
        <article class="detail-item">
          <h4>业务介绍</h4>
          <p>${escapeHtml(profile.business_intro || "-")}</p>
        </article>
        <article class="detail-item">
          <h4>产品介绍</h4>
          <p>${escapeHtml(profile.products_intro || "-")}</p>
        </article>
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
    const ticker = getTicker();
    if (!ticker) {
      renderNotFound("");
      return;
    }

    try {
      const data = await loadData();
      const profile = data.profiles?.[ticker];
      if (!profile) {
        renderNotFound(ticker);
        return;
      }
      renderStock(profile, data);
    } catch (error) {
      renderNotFound(ticker);
      // eslint-disable-next-line no-console
      console.error(error);
    }
  }

  bootstrap();
})();

