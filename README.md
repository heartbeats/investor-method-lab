# 投资方法论研究项目（investor-method-lab）

目标：系统化找到顶级投资人，抽取其分析方法，归类为可执行方法论，并用于选股与机会发现。

## 1. 项目能做什么

- 找到“长期可复用”投资人：按业绩、风控、周期长度、透明度综合打分
- 抽取方法论：把投资人的分析框架归类为策略标签
- 机会筛选：按策略权重对候选股票打分并输出机会池

> 仅用于研究与学习，不构成投资建议。

## 2. 目录结构

- `data/investors.json`：投资人数据库 + 排名权重
- `data/methodologies.json`：方法论分类、筛选规则、因子权重
- `data/opportunities.sample.csv`：候选机会样例数据
- `scripts/rank_investors.py`：投资人综合排名与方法论覆盖分析
- `scripts/rank_opportunities.py`：按策略输出机会池
- `docs/investor_note_template.md`：研究笔记模板
- `tests/`：基础单元测试

## 3. 快速开始

```bash
cd /home/afu/projects/investor-method-lab
python3 scripts/rank_investors.py --top 10
python3 scripts/rank_opportunities.py --strategy value_quality --top 8
python3 scripts/build_verified_investors.py --min-confidence B
python3 scripts/build_real_opportunities.py
python3 scripts/generate_top20_opportunity_pack.py --top 10 --per-group-top 5 --max-per-sector 2
bash scripts/run_real_pack_3markets.sh
python3 -m unittest discover -s tests
```

`build_real_opportunities.py` 默认开启 24 小时缓存（`data/cache/yfinance`），用于非实时场景降低 API 限流风险；如需强制实时拉取可加 `--no-cache`。
可选接入 `stock-data-hub`：设置 `IML_STOCK_DATA_HUB_URL=http://127.0.0.1:18123` 后，脚本会按需从 hub 兜底 `quote/external_valuation/fundamental`（仅在 Yahoo 缺失时触发）。

`build_investor_profiles.py` 默认开启 24 小时缓存（`data/cache/holding_prices`），并按市场自动路由：
- A/HK：`Futu OpenD -> Yahoo Finance`
- US：`Futu OpenD(有权限时) -> yfinance -> FMP -> Alpha Vantage`
- 可用环境变量 `IML_US_QUOTE_PROVIDERS` 覆盖 US 回退顺序（如 `yfinance,fmp,alpha_vantage`）。
- 若设置 `IML_STOCK_DATA_HUB_URL`，报价会优先走 hub，再回退本地链路。

`build_real_opportunities.py` 默认会尝试复用本机 DCF 能力（`~/.codex/skills/dcf-valuation-link/scripts/dcf_valuation_link.py`）：
- 估值优先级：`dcf_iv_base > targetMeanPrice > close`
- 输出字段新增：`valuation_source`、`dcf_symbol`、`dcf_iv_base` 等
- 元信息新增：`dcf_integration`、`valuation_source_breakdown`

如需关闭 DCF 覆盖，可加 `--disable-dcf`；如需严格模式（DCF 拉取失败即报错）可加 `--dcf-strict`。

可用以下脚本批量补齐 DCF 覆盖（公司档案 + 财报快照 + 审核 + 估值）：

```bash
cd /home/afu/projects/investor-method-lab
python3 scripts/seed_dcf_coverage_from_universe.py \
  --universe-file data/opportunities.universe_3markets.csv \
  --report-file data/dcf_coverage_seed_report.json
```

说明：该脚本基于 `yfinance` 财报与行情，失败项会在报告里逐条列出原因。

### 网页看板（查看全部整理信息）

```bash
cd /home/afu/projects/investor-method-lab
# 先构建投资者资料库（含个人介绍、持仓价格/占比/更新时间/变动比例）
python3 scripts/build_investor_profiles.py
# 再构建数据源能力面板（自动探测各数据源可用性）
python3 scripts/build_data_source_catalog.py
# 构建富途对账报告（默认自动覆盖可对账投资人）
python3 scripts/build_futu_alignment_report.py
# 构建方法论V2草案（1主类+多标签）
python3 scripts/build_methodology_v2_draft.py
# 构建方法论V3正式口径（分轨+手工映射）
python3 scripts/build_methodology_v3.py

# 启动网页服务
bash scripts/run_dashboard.sh
```

浏览器打开：`http://127.0.0.1:8090/web/`
详情页示例：`http://127.0.0.1:8090/web/investor.html?id=warren_buffett`

若 8090 被占用，可指定端口：

```bash
bash scripts/run_dashboard.sh 8091
```

- 页面入口：`web/index.html`
- 详情页入口：`web/investor.html?id=<investor_id>`
- 方法论详情页：`web/method.html?family_id=<family_id>`
- 数据说明页：`web/data-info.html`
- 样式：`web/styles.css`
- 总览数据装载与交互：`web/app.js`
- 详情页渲染：`web/investor.js`
- 默认展示口径：`实时口径（A/HK/US）`
- 提醒：切换到“样本口径”时页面会明确标注“非真实数据”
- 补充名单：`data/investor_additional_watchlist.json`（段永平、李录、佩洛西、黄仁勋、木头姐、特朗普、马乔利·格林、乔什·哥特海默、吉尔·西斯内罗斯）
- 13F 深挖：脚本会优先使用“投资人->披露实体(CIK)”映射抓取最新 13F（当前已接入段永平/李录/木头姐）
- 口径边界：13F 仅覆盖美国可报告长仓，不包含非 13F 资产（如部分港股/A股、期权、现金等）
- OpenD 行情：若 `Futu OpenD` 可用，则优先用于 A/HK 行情；若 US 权限不足会自动回退 Yahoo，并在页面“数据源能力面板”显示权限状态。
- 数据源目录脚本会自动调用统一探测器：`/home/afu/.codex/skills/stock-data-fetch/scripts/probe_stock_sources.py`，并把 AkShare/FMP/Alpha/Tushare 的实测状态写入 `data/data_source_catalog.json` 与 `data/stock_provider_probe.json`。
- 覆盖主口径：全接口价格覆盖（Futu OpenD + Yahoo 等）优先，用于评估“是否拿到可用行情”。
- OpenD 口径：仅用于诊断富途权限/映射问题，不作为主覆盖能力结论。
- 富途对账报告：`data/futu_alignment_report.json`，同时展示“全接口覆盖率（主）+ OpenD 命中率（诊断）”。
- 方法论口径：网页优先读取 V3（`data/methodology_taxonomy_v3.json` + `data/investor_methodology_v3.json`），旧框架仅兜底。

## 4. 标准工作流

1. 每周更新投资人资料：业绩、最大回撤、公开材料完整度
2. 每两周审视方法论：新增/合并策略分类，更新因子权重
3. 每日更新候选池：导入候选股票数据
4. 跑机会筛选：按策略生成 top list，加入观察池
5. 复盘：记录命中率、错误原因、改进权重

## 5. 下一步扩展建议

- 接入真实行情和财报源（自动更新候选池）
- 引入回测模块（检验方法论是否稳健）
- 增加“市场阶段识别”层（牛/熊/震荡不同权重）

## 6. Top20 研究资产

- `data/top20_global_investors_10y_plus.json`：全球10年以上高年化投资人 Top20（含中文名）
- `docs/top20_methodology_playbook.md`：Top20 方法论分组 + 选股因子映射
- `data/top20_methodology_framework.json`：Top20 投资人方法论到执行分组映射
- `docs/top20_opportunity_pack.md`：方法论分组、因子权重、首批机会池 TOP10
- `output/top20_first_batch_opportunities.csv`：首批机会池结构化结果
- `output/top20_methodology_top5_by_group.csv`：各方法论分组 Top5 机会池
- `output/top20_diversified_opportunities.csv`：行业分散约束版 Top10（默认单行业最多 2 个）
- `data/opportunities.real.csv`：实时行情/财务口径生成的机会池输入
- `docs/opportunities_real_data_meta.json`：实时口径元信息与公式说明
- `docs/margin_of_safety_references.md`：安全边际口径对照（项目口径 + Yahoo/Investopedia/Wall Street Prep/Morningstar）

### 价值质量复利（巴芒口径）执行门槛

- 硬门槛：`margin_of_safety >= 15%`，且（有 `certainty_score` 时）`certainty_score >= 65`
- 软惩罚：`margin_of_safety < 30%` 或 `certainty_score < 75` 时下调该策略得分
- 说明：该门槛目前仅作用于 `value_quality_compound` 分组
- MOS 口径：`margin_of_safety = 1 - (price / fair_value)`（分母为 `fair_value`，保留负值）
- 口径换算：`upside_to_price = margin_of_safety / (1 - margin_of_safety)`

### 三市场覆盖（A/HK/US）

- 默认三市场股票池：`data/opportunities.universe_3markets.csv`
- 一键运行（实时数据 -> 机会包）：`bash scripts/run_real_pack_3markets.sh`
- 产物：
  - `data/opportunities.real_3markets.csv`
  - `docs/opportunities_real_data_meta_3markets.json`
  - `docs/top20_opportunity_pack_real_3markets.md`
  - `output/top20_first_batch_opportunities_real_3markets.csv`
  - `output/top20_methodology_top5_by_group_real_3markets.csv`
  - `output/top20_diversified_opportunities_real_3markets.csv`

## 7. 数据校准

- `data/top20_global_investors_10y_plus_calibrated.json`：Top20 校准版（含可信度、口径、代表持仓与持仓说明）
- `docs/data_calibration_notes_2026-02-27.md`：校准说明与关键修正
- `data/top20_global_investors_verified_ab.json`：可审计版（仅 A/B）
- `docs/top20_global_investors_verified_ab.md`：可审计榜单报告
- `docs/top20_verification_backlog.md`：C 级待核验清单
- `data/top20_global_investors_verified_a_only.json`：最严格版（仅 A）
- `scripts/enrich_investor_holding_weights.py`：补充“代表持仓占比”字段（优先 SEC 13F 可核验口径）

```bash
cd /home/afu/projects/investor-method-lab
python3 scripts/enrich_investor_holding_weights.py \
  --input data/top20_global_investors_10y_plus_calibrated.json \
  --output data/top20_global_investors_10y_plus_calibrated.json
```

说明：该脚本仅能覆盖公开 13F 的美国长仓股票占比；宏观/期货/非美股/历史仓位会标记为“未披露/不适用”或“13F 未命中”。

## 8. PAI 迭代闭环（已落地）

- 核心脚本：`scripts/pai_loop.py`
- 守护脚本（失败告警）：`scripts/pai_loop_guard.sh`
- 落地说明：`docs/pai_landing_plan.md`
- 定时安装：`scripts/install_pai_loop_cron.sh`

```bash
cd /home/afu/projects/investor-method-lab

# 默认闭环：样例数据路径（非真实数据口径）
python3 scripts/pai_loop.py

# 实时数据闭环：包含 Yahoo Finance 刷新
python3 scripts/pai_loop.py --with-real-data

# 守护模式（失败自动告警；支持 sample/real）
bash scripts/pai_loop_guard.sh sample
bash scripts/pai_loop_guard.sh real

# 可选：配置飞书告警（供 cron 使用）
cat > .env.pai <<'EOF'
PAI_FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx'
# 或复用 ~/.config/dcf_notify.env 的 app 发送配置
# PAI_NOTIFY_ENV_FILE="$HOME/.config/dcf_notify.env"
EOF

# 查看计划任务状态 / 安装定时任务
bash scripts/install_pai_loop_cron.sh status
bash scripts/install_pai_loop_cron.sh apply
```

- 当前定时策略：仅 `real`（默认每天 09:10，可用 `PAI_REAL_CRON` 覆盖）
- 闭环报告输出：`output/pai_loop/latest_report.md`
- 历史运行记录：`output/pai_loop/runs.jsonl`
- 告警日志：`output/pai_loop/alert.log`
