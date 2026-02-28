# Top20 数据校准说明（2026-02-27）

## 结论

原始 Top20 数据可用于“研究启发”，但不适合作为“严格可比排名”。
主要问题是：

- 混用了净收益、毛收益、税前收益、以及区间内择优年份；
- 部分数据来自单一历史引述，缺少独立复核；
- “重仓资产”里混有“历史代表持仓”与“当前持仓”，语义未分层。

## 已做校准

新增文件：

- `data/top20_global_investors_10y_plus_calibrated.json`

校准动作：

- 对每位投资人增加 `return_basis` 与 `confidence`；
- 对关键错误项做修正（Ackman、Loeb、Schloss）；
- 新增 `source_legend`，明确每条可追踪来源。

## 三个关键修正

1. Bill Ackman: `27.7%(2004-2014 gross)` -> `16.1%(2004-2024 net after performance fees)`
2. Dan Loeb: `20%+` -> `13.2% net (since Dec 1996)`
3. Walter Schloss: `20%` -> `15.3% (multi-decade full record)`

## 第二轮修正（你确认后继续推进）

新增升级对象（原 C -> B/A）：

1. Paul Tudor Jones：更新为 `24.0% net annualized (1986-2012)`，`B`
2. Bruce Kovner：更新为 `33.1% (1995-2003 primary speech window)`，`B`
3. Seth Klarman：更新为 `19.0% annualized (1983-2010 oldest partnership)`，`B`
4. Howard Marks：更新为 `15.7% net IRR (1988-2024, SEC strategy track record)`，`A`
5. Mohnish Pabrai：更新为 `15.0%`（由 Forbes 累计净收益推导年化，2000-2013），`B`

结果变化：

- `A/B` 可审计样本：`11 -> 16`
- `A-only` 最严格样本：`2 -> 3`
- 待核验 `C` 样本：`9 -> 4`

## 第三轮修正（继续压降 C 级）

新增升级对象（原 C -> B）：

1. Michael Steinhardt：`24.0% annualized after fees (1967-1995)`，`B`
2. Leon Levy：`22.4% annualized (1982-1997 Odyssey Partners)`，`B`
3. Shelby Davis：`22.1% derived annualized`（基于官方“$100k -> >$800m，~45年”描述），`B`

结果变化：

- `A/B` 可审计样本：`16 -> 19`
- 待核验 `C` 样本：`4 -> 1`（仅剩 Peter Brandt）

未完成项：

- （历史记录）第三轮结束时 Peter Brandt 仍为 `C`；该项已在第四轮完成升级。

## 第四轮修正（清零 C 级）

新增升级对象（原 C -> B）：

1. Peter Brandt：更新为 `58.0% annualized compounded`（late 1981 起、累计 27 个活跃交易年），`B`
2. 同步保留交叉参考：Benzinga 对 `Factor LLC` 的“last audit 41% compound”口径（用于解释不同样本窗口）

结果变化：

- `A/B` 可审计样本：`19 -> 20`
- 待核验 `C` 样本：`1 -> 0`

## 使用建议

- 如果做“谁最强”比较，先统一到“净收益 + 全周期 + 同费率口径”；
- 如果做“方法论学习”，当前校准数据已够用；
- 如需机构级精度，下一步应把每位的原始年化表（按年份）拉齐再排序。
