# Top20 方法论机会包

更新时间：2026-03-05

## 1) 方法论分组

| 分组 | 核心问题 | 代表投资人 | 人数 | 组合权重 |
|---|---|---|---:|---:|
| 价值质量复利 | 能否以安全边际买入长期复利型优质公司？ | 沃伦·巴菲特、查理·芒格 | 2 | 10.0% |
| 行业复利 | 行业结构优势是否能持续转化为长期复利？ | 谢尔比·戴维斯 | 1 | 5.0% |
| GARP 成长 | 是否以合理估值买入可持续成长？ | 彼得·林奇 | 1 | 5.0% |
| 深度价值修复 | 是否存在错杀带来的非对称修复机会？ | 塞思·卡拉曼、沃尔特·施洛斯、莫尼什·帕伯莱 | 3 | 15.0% |
| 宏观周期 | 当前宏观状态最受益的方向在哪里？ | 布鲁斯·科夫纳、乔治·索罗斯、斯坦利·德鲁肯米勒、迈克尔·斯坦哈特、保罗·都铎·琼斯 | 5 | 25.0% |
| 趋势跟随 | 主趋势是否足够清晰且可交易？ | 彼得·布兰特 | 1 | 5.0% |
| 系统化量化 | 规则化因子组合是否能稳定获取超额？ | 乔尔·格林布拉特、詹姆斯·西蒙斯 | 2 | 10.0% |
| 事件驱动激进 | 催化事件能否驱动估值重估？ | 史蒂文·科恩、里昂·利维、比尔·阿克曼、丹·勒布 | 4 | 20.0% |
| 信用周期 | 信用扩张/收缩对胜率的影响是什么？ | 霍华德·马克斯 | 1 | 5.0% |

## 2) 因子权重

| 分组 | 安全边际 | 质量 | 成长 | 趋势 | 催化 | 风控 |
|---|---:|---:|---:|---:|---:|---:|
| 价值质量复利 | 30.0% | 28.0% | 8.0% | 4.0% | 14.0% | 16.0% |
| 行业复利 | 20.0% | 26.0% | 20.0% | 8.0% | 12.0% | 14.0% |
| GARP 成长 | 16.0% | 20.0% | 32.0% | 10.0% | 14.0% | 8.0% |
| 深度价值修复 | 36.0% | 12.0% | 4.0% | 5.0% | 22.0% | 21.0% |
| 宏观周期 | 8.0% | 12.0% | 12.0% | 24.0% | 26.0% | 18.0% |
| 趋势跟随 | 5.0% | 8.0% | 13.0% | 41.0% | 23.0% | 10.0% |
| 系统化量化 | 25.0% | 24.0% | 9.0% | 9.0% | 12.0% | 21.0% |
| 事件驱动激进 | 13.0% | 16.0% | 8.0% | 11.0% | 34.0% | 18.0% |
| 信用周期 | 22.0% | 12.0% | 8.0% | 19.0% | 20.0% | 19.0% |

### 执行规则（统一口径）

| 分组 | 硬筛条件 | 软惩罚 |
|---|---|---|
| 价值质量复利 | MOS>=15%，质量>=65；若有确定性分则>=65。 | MOS<30% 折扣0.88；确定性<75 折扣0.92。 |
| 行业复利 | MOS>=5%，质量>=70，风控>=45%。 | 成长<55 折扣0.93；催化<50 折扣0.95。 |
| GARP 成长 | 成长>=55，质量>=60，P/FV<=1.25，风控>=35%。 | P/FV>1.05 折扣0.90；趋势<55 折扣0.93。 |
| 深度价值修复 | MOS>=20%，催化>=50，风控>=30%。 | 质量<45 折扣0.90；趋势<40 折扣0.92。 |
| 宏观周期 | 趋势>=55，催化>=55，风控>=30%。 | 成长<45 折扣0.95；MOS<0 折扣0.95。 |
| 趋势跟随 | 趋势>=70，催化>=60，风控>=30%。 | P/FV>1.20 折扣0.90；质量<45 折扣0.93。 |
| 系统化量化 | 质量/成长/趋势/催化均>=45，风控>=35%。 | MOS<0 折扣0.93。 |
| 事件驱动激进 | 催化>=55，趋势>=40，风控>=30%，且P/FV<=1.80。 | MOS<5% 折扣0.95；质量<50 折扣0.95。 |
| 信用周期 | MOS>=5%，催化>=50，风控>=45%。 | 趋势<50 折扣0.95；质量<45 折扣0.95。 |

## 3) 首批机会池 TOP10（组合评分）

| 排名 | 代码 | 公司 | 行业 | 组合分 | 最匹配方法论 | 理由 | 备注 |
|---|---|---|---|---:|---|---|---|
| 1 | HPE | Hewlett Packard Enterprise | Technology | 71.29 | 宏观周期 | 催化:19.5 \| 风控:16.1 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=21.55 \| target=26.01 \| fv_source=target_mean_price \| upside=20.7% |
| 2 | 000002.SZ | 万科A | Real Estate | 64.42 | 宏观周期 | 趋势:23.6 \| 催化:16.2 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-04 \| close=4.62 \| target=5.30 \| fv_source=target_mean_price \| upside=14.7% |
| 3 | HPQ | HP Inc. | Technology | 57.97 | 宏观周期 | 趋势:23.2 \| 催化:22.9 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=19.18 \| target=19.99 \| fv_source=target_mean_price \| upside=4.2% |
| 4 | 688036.SS | 传音控股 | Technology | 56.07 | 宏观周期 | 催化:25.1 \| 趋势:23.9 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-04 \| close=53.15 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 5 | CPB | Campbell's Company (The) | Consumer Defensive | 54.79 | 宏观周期 | 趋势:22.5 \| 催化:18.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=25.09 \| target=30.89 \| fv_source=target_mean_price \| upside=23.1% |
| 6 | 603260.SS | 合盛硅业 | Basic Materials | 54.53 | 宏观周期 | 催化:25.2 \| 趋势:19.0 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-04 \| close=48.20 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 7 | LEN | Lennar | Consumer Cyclical | 53.46 | 宏观周期 | 催化:24.8 \| 趋势:21.4 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=106.53 \| target=108.71 \| fv_source=target_mean_price \| upside=2.1% |
| 8 | BAX | Baxter International | Healthcare | 52.19 | 宏观周期 | 趋势:21.2 \| 催化:18.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=19.03 \| target=21.63 \| fv_source=target_mean_price \| upside=13.7% |
| 9 | 00732.HK | TRULY INT'L | Technology | 49.91 | 宏观周期 | 催化:22.7 \| 趋势:20.6 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=0.96 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 10 | FOXA | Fox Corporation (Class A) | Communication Services | 48.94 | 宏观周期 | 趋势:18.8 \| 催化:17.8 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=58.42 \| target=71.76 \| fv_source=target_mean_price \| upside=22.8% |

## 4) 各方法论 Top5 机会池

### 价值质量复利

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | 00881.HK | ZHONGSHENG HLDG | Consumer Cyclical | 83.66 | 安全边际:28.5 \| 质量:24.8 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=9.80 \| target=18.32 \| fv_source=target_mean_price \| upside=86.9% |
| 2 | APTV | Aptiv | Consumer Cyclical | 82.28 | 安全边际:28.3 \| 质量:26.4 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=73.39 \| target=100.88 \| fv_source=target_mean_price \| upside=37.5% |
| 3 | 00656.HK | FOSUN INTL | Industrials | 81.62 | 质量:26.1 \| 安全边际:25.4 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=3.67 \| target=5.46 \| fv_source=target_mean_price \| upside=48.9% |
| 4 | 00763.HK | ZTE | Technology | 81.04 | 安全边际:25.1 \| 质量:21.2 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=26.10 \| target=38.19 \| fv_source=target_mean_price \| upside=46.3% |
| 5 | 300122.SZ | 智飞生物 | Healthcare | 80.75 | 安全边际:29.3 \| 质量:25.4 | A core \| CSI300 constituent \| weight=0.080% \| real-data@2026-03-04 \| close=15.63 \| target=24.78 \| fv_source=target_mean_price \| upside=58.5% |

### 行业复利

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | HPE | Hewlett Packard Enterprise | Technology | 83.30 | 质量:25.1 \| 成长:17.0 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=21.55 \| target=26.01 \| fv_source=target_mean_price \| upside=20.7% |
| 2 | 000002.SZ | 万科A | Real Estate | 83.00 | 质量:25.8 \| 安全边际:15.5 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-04 \| close=4.62 \| target=5.30 \| fv_source=target_mean_price \| upside=14.7% |
| 3 | 00763.HK | ZTE | Technology | 82.75 | 质量:19.7 \| 成长:18.6 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=26.10 \| target=38.19 \| fv_source=target_mean_price \| upside=46.3% |
| 4 | 00656.HK | FOSUN INTL | Industrials | 82.21 | 质量:24.2 \| 安全边际:17.0 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=3.67 \| target=5.46 \| fv_source=target_mean_price \| upside=48.9% |
| 5 | 00341.HK | CAFE DE CORAL H | Consumer Cyclical | 81.10 | 质量:22.8 \| 成长:19.6 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-04 \| close=4.65 \| target=7.99 \| fv_source=target_mean_price \| upside=71.8% |

### GARP 成长

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 90.52 | 成长:31.9 \| 质量:18.4 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=95.99 \| target=127.29 \| fv_source=target_mean_price \| upside=32.6% |
| 2 | 00341.HK | CAFE DE CORAL H | Consumer Cyclical | 84.27 | 成长:31.3 \| 质量:17.5 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-04 \| close=4.65 \| target=7.99 \| fv_source=target_mean_price \| upside=71.8% |
| 3 | 00881.HK | ZHONGSHENG HLDG | Consumer Cyclical | 84.01 | 成长:30.3 \| 质量:17.7 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=9.80 \| target=18.32 \| fv_source=target_mean_price \| upside=86.9% |
| 4 | 00763.HK | ZTE | Technology | 83.62 | 成长:29.7 \| 质量:15.1 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=26.10 \| target=38.19 \| fv_source=target_mean_price \| upside=46.3% |
| 5 | 603260.SS | 合盛硅业 | Basic Materials | 83.61 | 成长:31.8 \| 质量:18.6 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-04 \| close=48.20 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

### 深度价值修复

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 85.79 | 安全边际:32.2 \| 风控:20.1 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=95.99 \| target=127.29 \| fv_source=target_mean_price \| upside=32.6% |
| 2 | 00763.HK | ZTE | Technology | 80.90 | 安全边际:30.1 \| 风控:19.1 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=26.10 \| target=38.19 \| fv_source=target_mean_price \| upside=46.3% |
| 3 | GPN | Global Payments | Industrials | 75.50 | 安全边际:31.9 \| 风控:16.2 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=77.57 \| target=101.85 \| fv_source=target_mean_price \| upside=31.3% |
| 4 | AJG | Arthur J. Gallagher & Co. | Financial Services | 72.78 | 安全边际:29.7 \| 催化:13.7 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=225.58 \| target=281.94 \| fv_source=target_mean_price \| upside=25.0% |
| 5 | CPB | Campbell's Company (The) | Consumer Defensive | 71.34 | 安全边际:28.6 \| 催化:15.5 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=25.09 \| target=30.89 \| fv_source=target_mean_price \| upside=23.1% |

### 宏观周期

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | 688036.SS | 传音控股 | Technology | 87.74 | 催化:25.1 \| 趋势:23.9 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-04 \| close=53.15 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 2 | LEN | Lennar | Consumer Cyclical | 82.86 | 催化:24.8 \| 趋势:21.4 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=106.53 \| target=108.71 \| fv_source=target_mean_price \| upside=2.1% |
| 3 | 603260.SS | 合盛硅业 | Basic Materials | 82.77 | 催化:25.2 \| 趋势:19.0 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-04 \| close=48.20 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 4 | 000002.SZ | 万科A | Real Estate | 81.89 | 趋势:23.6 \| 催化:16.2 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-04 \| close=4.62 \| target=5.30 \| fv_source=target_mean_price \| upside=14.7% |
| 5 | HPQ | HP Inc. | Technology | 81.39 | 趋势:23.2 \| 催化:22.9 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=19.18 \| target=19.99 \| fv_source=target_mean_price \| upside=4.2% |

### 趋势跟随

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | 688036.SS | 传音控股 | Technology | 91.71 | 趋势:40.8 \| 催化:22.2 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-04 \| close=53.15 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 2 | LEN | Lennar | Consumer Cyclical | 86.38 | 趋势:36.6 \| 催化:22.0 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=106.53 \| target=108.71 \| fv_source=target_mean_price \| upside=2.1% |
| 3 | HPQ | HP Inc. | Technology | 84.91 | 趋势:39.7 \| 催化:20.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=19.18 \| target=19.99 \| fv_source=target_mean_price \| upside=4.2% |
| 4 | 603260.SS | 合盛硅业 | Basic Materials | 83.92 | 趋势:32.5 \| 催化:22.3 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-04 \| close=48.20 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 5 | 00732.HK | TRULY INT'L | Technology | 81.53 | 趋势:35.2 \| 催化:20.1 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=0.96 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

### 系统化量化

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 89.50 | 安全边际:22.4 \| 质量:22.0 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=95.99 \| target=127.29 \| fv_source=target_mean_price \| upside=32.6% |
| 2 | 000002.SZ | 万科A | Real Estate | 83.79 | 质量:23.8 \| 安全边际:19.4 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-04 \| close=4.62 \| target=5.30 \| fv_source=target_mean_price \| upside=14.7% |
| 3 | HPE | Hewlett Packard Enterprise | Technology | 82.56 | 质量:23.2 \| 风控:18.7 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=21.55 \| target=26.01 \| fv_source=target_mean_price \| upside=20.7% |
| 4 | 00763.HK | ZTE | Technology | 82.48 | 安全边际:20.9 \| 风控:19.1 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=26.10 \| target=38.19 \| fv_source=target_mean_price \| upside=46.3% |
| 5 | 00656.HK | FOSUN INTL | Industrials | 81.83 | 质量:22.4 \| 安全边际:21.2 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=3.67 \| target=5.46 \| fv_source=target_mean_price \| upside=48.9% |

### 事件驱动激进

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | HPE | Hewlett Packard Enterprise | Technology | 80.16 | 催化:25.6 \| 风控:16.1 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=21.55 \| target=26.01 \| fv_source=target_mean_price \| upside=20.7% |
| 2 | 000002.SZ | 万科A | Real Estate | 79.02 | 催化:21.3 \| 质量:15.9 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-04 \| close=4.62 \| target=5.30 \| fv_source=target_mean_price \| upside=14.7% |
| 3 | 688036.SS | 传音控股 | Technology | 79.01 | 催化:32.8 \| 风控:16.4 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-04 \| close=53.15 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 4 | AES | AES Corporation | Utilities | 78.88 | 催化:29.3 \| 质量:15.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=14.29 \| target=16.33 \| fv_source=target_mean_price \| upside=14.3% |
| 5 | 603260.SS | 合盛硅业 | Basic Materials | 77.83 | 催化:32.9 \| 质量:14.9 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-04 \| close=48.20 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

### 信用周期

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 87.39 | 安全边际:19.7 \| 风控:18.1 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=95.99 \| target=127.29 \| fv_source=target_mean_price \| upside=32.6% |
| 2 | 00763.HK | ZTE | Technology | 82.33 | 安全边际:18.4 \| 风控:17.3 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-05 \| close=26.10 \| target=38.19 \| fv_source=target_mean_price \| upside=46.3% |
| 3 | 000002.SZ | 万科A | Real Estate | 82.00 | 趋势:18.7 \| 安全边际:17.1 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-04 \| close=4.62 \| target=5.30 \| fv_source=target_mean_price \| upside=14.7% |
| 4 | HPE | Hewlett Packard Enterprise | Technology | 78.18 | 风控:16.9 \| 安全边际:16.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=21.55 \| target=26.01 \| fv_source=target_mean_price \| upside=20.7% |
| 5 | BAX | Baxter International | Healthcare | 75.73 | 趋势:16.8 \| 风控:16.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=19.03 \| target=21.63 \| fv_source=target_mean_price \| upside=13.7% |

## 5) 行业分散约束版 TOP10（单行业最多 2 个）

| 排名 | 代码 | 公司 | 行业 | 组合分 | 最匹配方法论 | 理由 | 备注 |
|---|---|---|---|---:|---|---|---|
| 1 | HPE | Hewlett Packard Enterprise | Technology | 71.29 | 宏观周期 | 催化:19.5 \| 风控:16.1 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=21.55 \| target=26.01 \| fv_source=target_mean_price \| upside=20.7% |
| 2 | 000002.SZ | 万科A | Real Estate | 64.42 | 宏观周期 | 趋势:23.6 \| 催化:16.2 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-04 \| close=4.62 \| target=5.30 \| fv_source=target_mean_price \| upside=14.7% |
| 3 | HPQ | HP Inc. | Technology | 57.97 | 宏观周期 | 趋势:23.2 \| 催化:22.9 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=19.18 \| target=19.99 \| fv_source=target_mean_price \| upside=4.2% |
| 4 | CPB | Campbell's Company (The) | Consumer Defensive | 54.79 | 宏观周期 | 趋势:22.5 \| 催化:18.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=25.09 \| target=30.89 \| fv_source=target_mean_price \| upside=23.1% |
| 5 | 603260.SS | 合盛硅业 | Basic Materials | 54.53 | 宏观周期 | 催化:25.2 \| 趋势:19.0 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-04 \| close=48.20 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 6 | LEN | Lennar | Consumer Cyclical | 53.46 | 宏观周期 | 催化:24.8 \| 趋势:21.4 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=106.53 \| target=108.71 \| fv_source=target_mean_price \| upside=2.1% |
| 7 | BAX | Baxter International | Healthcare | 52.19 | 宏观周期 | 趋势:21.2 \| 催化:18.3 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=19.03 \| target=21.63 \| fv_source=target_mean_price \| upside=13.7% |
| 8 | FOXA | Fox Corporation (Class A) | Communication Services | 48.94 | 宏观周期 | 趋势:18.8 \| 催化:17.8 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=58.42 \| target=71.76 \| fv_source=target_mean_price \| upside=22.8% |
| 9 | KHC | Kraft Heinz | Consumer Defensive | 48.77 | 宏观周期 | 催化:24.2 \| 趋势:19.4 | US core \| S&P500 constituent \| real-data@2026-03-04 \| close=24.04 \| target=25.13 \| fv_source=target_mean_price \| upside=4.5% |
| 10 | 601618.SS | 中国中冶 | Industrials | 48.76 | 宏观周期 | 催化:25.0 \| 趋势:14.4 | A core \| CSI300 constituent \| weight=0.089% \| real-data@2026-03-04 \| close=3.09 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

## 6) 安全边际口径参照

- 项目主口径：`MOS_FV = (FV - P) / FV = 1 - P/FV`（分母为 FV，保留负值）。
- 常见目标价口径：`UPSIDE_P = (FV - P) / P = FV/P - 1`（分母为现价 P）。
- 口径换算：`UPSIDE_P = MOS_FV / (1 - MOS_FV)`；`MOS_FV = UPSIDE_P / (1 + UPSIDE_P)`。
- Yahoo 参照：页面常见 `1y Target Est`（分析师一年目标价），通常按 `UPSIDE_P` 解读。
- Morningstar 参照：常见 `Price/Fair Value`；折价口径可写为 `1 - Price/Fair Value`。
- 详细来源与说明：`docs/margin_of_safety_references.md`。