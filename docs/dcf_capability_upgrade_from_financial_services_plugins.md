# DCF 能力强化学习笔记（anthropics/financial-services-plugins）

更新时间：2026-03-05  
学习源：`https://github.com/anthropics/financial-services-plugins`

## 1) 结论先行

- 该仓库最值得借鉴的不是“具体数据源”，而是**工作流编排标准**：
  - 先 `Comps`，再 `DCF`，最后 `Cross-check`；
  - 每个任务有前置依赖，不允许跳步；
  - 输出必须是可审计产物（模型 + 摘要 +敏感性）。
- 对我们当前 DCF 体系，能立即落地的是：
  - DCF 与可比估值联动校验；
  - 估值质量闸门（终值占比、隐含倍数偏离、敏感性完整性）；
  - 报告结构标准化（假设来源、关键风险、结论区间）。
- 需要谨慎参考的是：
  - 其 MCP 连接器大多是机构级付费数据，不适合作为我们的默认基础源。

## 2) 可直接复用到我们系统的能力

## 2.1 三段式估值流程（建议固化为默认）

1. `Comps 基线`：先拿行业可比倍数（EV/EBITDA、P/E）做锚。  
2. `DCF 主估值`：输出三档场景（悲观/中性/乐观）与安全边际。  
3. `Cross-check`：校验 DCF 隐含倍数与 Comps 是否严重偏离。

这与我们当前“单 DCF 主导”相比，能显著降低参数失真导致的偏差。

## 2.2 估值质量闸门（推荐新增到日报前置检查）

- 终值占 EV 比例超阈值（例如 >75%）直接降级为“需复核”。
- DCF 隐含 EV/EBITDA 与行业中位数偏离过大（例如 >2 个标准差）触发告警。
- 敏感性矩阵必须完整（至少 `r × g_terminal` 二维），否则不出正式结论。
- 输出必须给“区间”而非单点值（避免伪精确）。

## 2.3 任务依赖治理（避免错误链路）

- 未完成财务输入校验，不允许跑估值。
- 未完成估值，不允许推送“机会结论”。
- 推送内容必须可回溯到输入文件和时间戳。

## 3) 可以参考但不应直接照搬的部分

## 3.1 机构级连接器

仓库里提到的 Daloopa、Morningstar、FactSet、PitchBook 等，很多都需要机构授权。  
我们当前更适合的默认组合仍是：`Futu/OpenD + Yahoo + AkShare + FMP + Alpha + Tushare`（按市场路由）。

## 3.2 Excel 生产标准

仓库强调“投行级 Excel 交付规范”（含大量格式规则、批注规范、75 格敏感性填充）。  
我们可以吸收其 QC 思路，但无需完全复制其文档密度和产物形态。

## 4) 对我们现有项目的落地动作（下一阶段）

1. 在 `hit-zone` 增加 `comps_crosscheck` 结构化输出（隐含倍数 vs 行业锚）。  
2. 在日报推送前增加 `valuation_quality_gate`（终值占比、隐含倍数偏离、敏感性完整性）。  
3. 将“特别关注 / 机会挖掘”两模块都绑定输入来源元数据（文件、as-of、口径）。  
4. 后续若接入机构数据，统一走 `stock-data-hub` 扩展层，不把供应商耦合进业务脚本。

## 4.1 当前落地进度（2026-03-05）

- 已完成：`hit-zone` 输出 `valuation_quality_gate` 与 `comps_crosscheck` 结构化字段，并接入 dashboard 展示。
- 已完成：日报拆分为 `特别关注` / `机会挖掘` 双模块，且输出来源元信息。
- 已完成：`stock-data-hub` 新增 `POST /v1/comps-baselines`，并在 `build_real_opportunities.py` 接入“仅补充型 fallback overlay”。
  - 规则：仅当 `dcf_comps_crosscheck_status` 缺失时补齐；
  - 不覆盖已有 DCF cross-check；
  - 回写 `dcf_comps_source=stock_data_hub_comps_baseline`，便于前端区分来源。
- 已完成：新增可选 peers 策略 `sector_size`（同市场内“同板块优先 + 市值接近排序”），通过 `POST /v1/fundamentals` 批量市值做约束；默认策略保持 `sector_market` 以确保兼容。
- 待推进：更精细行业分层 peers（当前以“同市场+同板块优先”自动构建 peers，已可用但仍可继续精细化）。

## 5) 与当前系统的关系

- 当前已完成：日报推送拆分为
  - `特别关注（深度 DCF 校准清单）`
  - `机会挖掘（剔除特别关注后的新增候选）`
- 本文档定义的是下一阶段“提升估值质量”的标准，不改你已确认的 DCF 参数口径偏好。
