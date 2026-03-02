# 安全边际口径参照（MOS）

更新时间：2026-03-01

## 1) 本项目主口径（已生效）

- 记号：`P` = 当前价格（price）；`FV` = 公允价值/内在价值（fair value，本项目真实数据流中默认代理为 Yahoo `targetMeanPrice`，缺失时回退 `close`）
- 公式：`MOS_FV = (FV - P) / FV = 1 - P/FV`
- 规则：保留负值。`P > FV` 时 `MOS_FV < 0`，可直接表示“高估比例”。

## 2) 常见外部口径

| 口径名称 | 公式 | 说明 |
|---|---|---|
| FV 分母 MOS（本项目主口径） | `(FV - P) / FV` | 低估时为正，高估时为负 |
| 价格分母 Upside（目标价常见） | `(FV - P) / P = FV/P - 1` | 常用于“上行空间”展示 |
| Price/Fair Value 折价（Morningstar 常见） | `1 - P/FV` | 与本项目主口径等价 |

## 3) 两套口径换算

- `UPSIDE_P = MOS_FV / (1 - MOS_FV)`
- `MOS_FV = UPSIDE_P / (1 + UPSIDE_P)`

示例（保留负值）：

| 场景 | P | FV | MOS_FV | UPSIDE_P |
|---|---:|---:|---:|---:|
| 低估 | 80 | 100 | 20.00% | 25.00% |
| 高估 | 120 | 100 | -20.00% | -16.67% |

## 4) Yahoo 口径说明（参照）

- Yahoo Finance 报价页通常展示 `1y Target Est`（分析师一年目标价）。
- Yahoo 页面本身不直接给“安全边际 MOS”公式；行业里常用的是 `UPSIDE_P = (Target - Price)/Price`。
- 在本项目中，若使用 Yahoo 字段做参照，采用：
- `FV_proxy = targetMeanPrice`
- `MOS_FV = (FV_proxy - P) / FV_proxy`
- `UPSIDE_P = (FV_proxy - P) / P`

## 5) 参考来源

- Yahoo Finance Quote（示例，含 `1y Target Est`）：https://finance.yahoo.com/quote/AAPL
- Investopedia（MOS 定义）：https://www.investopedia.com/terms/m/marginofsafety.asp
- Wall Street Prep（MOS 公式）：https://www.wallstreetprep.com/knowledge/margin-of-safety/
- Morningstar Glossary（Discount to Fair Value）：https://awgmain.morningstar.com/webhelp/glossary_definitions/mutual_fund/f_3131_Discount_to_Fair_Value.html
- Morningstar Glossary（Price/Fair Value）：https://awgmain.morningstar.com/webhelp/glossary_definitions/mutual_fund/mfglossary_Price_Fair_Value.html
