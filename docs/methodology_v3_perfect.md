# 方法论分类 V3（建议作为正式口径）

更新时间：2026-03-02

## 核心结论

V3 相比 V2 的改进点：

1. 主体分轨：投资方法主体与披露跟踪主体完全拆分，不再混排。
2. 主类更干净：拆开“主观宏观”和“趋势跟随”，避免语义混淆。
3. 误标修复：收益标签收紧为“净口径可核验 / 公开资料口径 / 13F代理”，避免过度宣称可审计。
4. 可执行：每个主体固定 `1 主家族 + N 执行标签 + N 披露标签`，可直接驱动筛选器和机会池分层。

## 产物

- 分类字典：[`methodology_taxonomy_v3.json`](/home/afu/projects/investor-method-lab/data/methodology_taxonomy_v3.json)
- 映射结果：[`investor_methodology_v3.json`](/home/afu/projects/investor-method-lab/data/investor_methodology_v3.json)
- 生成脚本：[`build_methodology_v3.py`](/home/afu/projects/investor-method-lab/scripts/build_methodology_v3.py)

## 当前统计（29个主体）

1. 投资方法主体：23
2. 披露跟踪主体：6
3. 可直接用于选股：23
4. 仅观察用途：6
5. 分类校验问题：0

## 关键样例（已修复的误分点）

1. Peter Brandt：归入“趋势跟随”（非宏观）。
2. Soros / Druckenmiller：主类“主观宏观”，趋势作为次级特征。
3. Walter Schloss：深度价值，不再默认强加“事件催化”。
4. Jensen Huang：归入“管理层持股敞口跟踪”，标记“非完整组合披露”。
5. Donald Trump：归入“公众人物关联资产跟踪”，仅 observation。

## 用法建议

1. 主榜单（选股）只用 `track_id=investment_method`。
2. 披露主体单独做“行为信号看板”，不参与方法论回测。
3. 前端筛选使用三维：
   - 主家族（primary_family）
   - 执行标签（execution_tags）
   - 披露标签（disclosure_tags）

