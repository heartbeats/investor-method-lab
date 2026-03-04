# Top20 方法论机会包

更新时间：2026-02-27

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
| 1 | HPE | Hewlett Packard Enterprise | Technology | 70.77 | 宏观周期 | 催化:19.0 \| 风控:16.0 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=21.40 \| target=26.01 \| fv_source=target_mean_price \| upside=21.5% |
| 2 | 000002.SZ | 万科A | Real Estate | 62.80 | 宏观周期 | 趋势:23.8 \| 催化:16.7 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-03 \| close=4.67 \| target=5.30 \| fv_source=target_mean_price \| upside=13.4% |
| 3 | CARR | Carrier Global | Industrials | 62.68 | 宏观周期 | 催化:17.8 \| 风控:14.8 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=61.38 \| target=71.80 \| fv_source=target_mean_price \| upside=17.0% |
| 4 | HPQ | HP Inc. | Technology | 58.91 | 宏观周期 | 趋势:23.4 \| 催化:22.7 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=18.73 \| target=19.99 \| fv_source=target_mean_price \| upside=6.8% |
| 5 | BBY | Best Buy | Consumer Cyclical | 57.32 | 宏观周期 | 趋势:20.8 \| 催化:20.4 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=65.20 \| target=77.37 \| fv_source=target_mean_price \| upside=18.7% |
| 6 | 688036.SS | 传音控股 | Technology | 56.05 | 宏观周期 | 催化:25.1 \| 趋势:23.7 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-03 \| close=54.08 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 7 | 603260.SS | 合盛硅业 | Basic Materials | 54.46 | 宏观周期 | 催化:25.2 \| 趋势:18.8 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-03 \| close=48.97 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 8 | LEN | Lennar | Consumer Cyclical | 53.86 | 宏观周期 | 催化:25.3 \| 趋势:20.9 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=107.47 \| target=108.62 \| fv_source=target_mean_price \| upside=1.1% |
| 9 | KMX | CarMax | Consumer Cyclical | 52.53 | 宏观周期 | 催化:25.9 \| 趋势:20.5 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=41.02 \| target=39.23 \| fv_source=target_mean_price \| upside=-4.4% |
| 10 | IT | Gartner | Technology | 51.27 | 宏观周期 | 趋势:24.0 \| 催化:22.4 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=159.38 \| target=190.46 \| fv_source=target_mean_price \| upside=19.5% |

## 4) 各方法论 Top5 机会池

### 价值质量复利

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | 00881.HK | ZHONGSHENG HLDG | Consumer Cyclical | 83.55 | 安全边际:28.9 \| 质量:24.9 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=9.89 \| target=18.24 \| fv_source=target_mean_price \| upside=84.4% |
| 2 | APTV | Aptiv | Consumer Cyclical | 82.34 | 安全边际:28.7 \| 质量:26.2 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=70.56 \| target=101.25 \| fv_source=target_mean_price \| upside=43.5% |
| 3 | 00763.HK | ZTE | Technology | 81.19 | 安全边际:25.4 \| 质量:21.2 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=25.44 \| target=38.02 \| fv_source=target_mean_price \| upside=49.5% |
| 4 | 300122.SZ | 智飞生物 | Healthcare | 80.83 | 安全边际:29.8 \| 质量:25.4 | A core \| CSI300 constituent \| weight=0.080% \| real-data@2026-03-03 \| close=15.98 \| target=24.78 \| fv_source=target_mean_price \| upside=55.1% |
| 5 | 00656.HK | FOSUN INTL | Industrials | 80.29 | 质量:26.0 \| 安全边际:24.5 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=3.76 \| target=5.44 \| fv_source=target_mean_price \| upside=44.7% |

### 行业复利

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | 000002.SZ | 万科A | Real Estate | 83.58 | 质量:25.8 \| 安全边际:15.6 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-03 \| close=4.67 \| target=5.30 \| fv_source=target_mean_price \| upside=13.4% |
| 2 | 00763.HK | ZTE | Technology | 82.89 | 质量:19.7 \| 成长:18.6 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=25.44 \| target=38.02 \| fv_source=target_mean_price \| upside=49.5% |
| 3 | HPE | Hewlett Packard Enterprise | Technology | 82.60 | 质量:25.0 \| 成长:16.8 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=21.40 \| target=26.01 \| fv_source=target_mean_price \| upside=21.5% |
| 4 | 00656.HK | FOSUN INTL | Industrials | 81.27 | 质量:24.2 \| 成长:16.4 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=3.76 \| target=5.44 \| fv_source=target_mean_price \| upside=44.7% |
| 5 | 00341.HK | CAFE DE CORAL H | Consumer Cyclical | 80.78 | 质量:22.8 \| 成长:19.6 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=4.73 \| target=7.99 \| fv_source=target_mean_price \| upside=68.9% |

### GARP 成长

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 89.66 | 成长:31.9 \| 质量:18.1 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=97.87 \| target=127.29 \| fv_source=target_mean_price \| upside=30.1% |
| 2 | 00341.HK | CAFE DE CORAL H | Consumer Cyclical | 83.94 | 成长:31.3 \| 质量:17.5 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=4.73 \| target=7.99 \| fv_source=target_mean_price \| upside=68.9% |
| 3 | 00881.HK | ZHONGSHENG HLDG | Consumer Cyclical | 83.75 | 成长:30.3 \| 质量:17.7 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=9.89 \| target=18.24 \| fv_source=target_mean_price \| upside=84.4% |
| 4 | 00763.HK | ZTE | Technology | 83.70 | 成长:29.7 \| 质量:15.1 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=25.44 \| target=38.02 \| fv_source=target_mean_price \| upside=49.5% |
| 5 | 603260.SS | 合盛硅业 | Basic Materials | 83.61 | 成长:31.8 \| 质量:18.6 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-03 \| close=48.97 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

### 深度价值修复

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 84.21 | 安全边际:30.5 \| 风控:20.0 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=97.87 \| target=127.29 \| fv_source=target_mean_price \| upside=30.1% |
| 2 | 00763.HK | ZTE | Technology | 81.00 | 安全边际:30.5 \| 风控:19.2 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=25.44 \| target=38.02 \| fv_source=target_mean_price \| upside=49.5% |
| 3 | LKQ | LKQ Corporation | Consumer Cyclical | 75.91 | 安全边际:30.0 \| 风控:15.6 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=31.78 \| target=40.94 \| fv_source=target_mean_price \| upside=28.8% |
| 4 | GPN | Global Payments | Industrials | 74.71 | 安全边际:30.7 \| 风控:17.0 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=77.68 \| target=101.85 \| fv_source=target_mean_price \| upside=31.1% |
| 5 | AJG | Arthur J. Gallagher & Co. | Financial Services | 71.04 | 安全边际:28.5 \| 催化:13.6 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=225.28 \| target=281.94 \| fv_source=target_mean_price \| upside=25.2% |

### 宏观周期

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | 688036.SS | 传音控股 | Technology | 87.62 | 催化:25.1 \| 趋势:23.7 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-03 \| close=54.08 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 2 | BBY | Best Buy | Consumer Cyclical | 83.94 | 趋势:20.8 \| 催化:20.4 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=65.20 \| target=77.37 \| fv_source=target_mean_price \| upside=18.7% |
| 3 | KMX | CarMax | Consumer Cyclical | 83.69 | 催化:25.9 \| 趋势:20.5 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=41.02 \| target=39.23 \| fv_source=target_mean_price \| upside=-4.4% |
| 4 | IT | Gartner | Technology | 83.59 | 趋势:24.0 \| 催化:22.4 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=159.38 \| target=190.46 \| fv_source=target_mean_price \| upside=19.5% |
| 5 | 000002.SZ | 万科A | Real Estate | 82.67 | 趋势:23.8 \| 催化:16.7 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-03 \| close=4.67 \| target=5.30 \| fv_source=target_mean_price \| upside=13.4% |

### 趋势跟随

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | 688036.SS | 传音控股 | Technology | 91.47 | 趋势:40.5 \| 催化:22.2 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-03 \| close=54.08 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 2 | KMX | CarMax | Consumer Cyclical | 88.64 | 趋势:35.0 \| 催化:22.9 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=41.02 \| target=39.23 \| fv_source=target_mean_price \| upside=-4.4% |
| 3 | LEN | Lennar | Consumer Cyclical | 85.09 | 趋势:35.7 \| 催化:22.3 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=107.47 \| target=108.62 \| fv_source=target_mean_price \| upside=1.1% |
| 4 | HPQ | HP Inc. | Technology | 84.92 | 趋势:40.0 \| 催化:20.1 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=18.73 \| target=19.99 \| fv_source=target_mean_price \| upside=6.8% |
| 5 | 603260.SS | 合盛硅业 | Basic Materials | 83.53 | 趋势:32.0 \| 催化:22.3 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-03 \| close=48.97 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

### 系统化量化

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 88.12 | 质量:21.8 \| 安全边际:21.2 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=97.87 \| target=127.29 \| fv_source=target_mean_price \| upside=30.1% |
| 2 | 000002.SZ | 万科A | Real Estate | 84.33 | 质量:23.8 \| 安全边际:19.5 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-03 \| close=4.67 \| target=5.30 \| fv_source=target_mean_price \| upside=13.4% |
| 3 | 00763.HK | ZTE | Technology | 82.71 | 安全边际:21.2 \| 风控:19.2 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=25.44 \| target=38.02 \| fv_source=target_mean_price \| upside=49.5% |
| 4 | HPE | Hewlett Packard Enterprise | Technology | 81.96 | 质量:23.1 \| 风控:18.7 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=21.40 \| target=26.01 \| fv_source=target_mean_price \| upside=21.5% |
| 5 | BBY | Best Buy | Consumer Cyclical | 81.27 | 质量:19.6 \| 风控:19.5 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=65.20 \| target=77.37 \| fv_source=target_mean_price \| upside=18.7% |

### 事件驱动激进

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BBY | Best Buy | Consumer Cyclical | 81.95 | 催化:26.6 \| 风控:16.7 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=65.20 \| target=77.37 \| fv_source=target_mean_price \| upside=18.7% |
| 2 | KMX | CarMax | Consumer Cyclical | 80.96 | 催化:33.9 \| 风控:17.8 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=41.02 \| target=39.23 \| fv_source=target_mean_price \| upside=-4.4% |
| 3 | 000002.SZ | 万科A | Real Estate | 79.84 | 催化:21.8 \| 质量:15.9 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-03 \| close=4.67 \| target=5.30 \| fv_source=target_mean_price \| upside=13.4% |
| 4 | HPE | Hewlett Packard Enterprise | Technology | 79.39 | 催化:24.9 \| 风控:16.0 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=21.40 \| target=26.01 \| fv_source=target_mean_price \| upside=21.5% |
| 5 | 688036.SS | 传音控股 | Technology | 79.02 | 催化:32.8 \| 风控:16.4 | A core \| CSI300 constituent \| weight=0.129% \| real-data@2026-03-03 \| close=54.08 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

### 信用周期

| 排名 | 代码 | 公司 | 行业 | 组内分 | 理由 | 备注 |
|---|---|---|---|---:|---|---|
| 1 | BLDR | Builders FirstSource | Industrials | 86.34 | 安全边际:18.6 \| 风控:18.1 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=97.87 \| target=127.29 \| fv_source=target_mean_price \| upside=30.1% |
| 2 | 000002.SZ | 万科A | Real Estate | 82.71 | 趋势:18.8 \| 安全边际:17.2 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-03 \| close=4.67 \| target=5.30 \| fv_source=target_mean_price \| upside=13.4% |
| 3 | 00763.HK | ZTE | Technology | 82.53 | 安全边际:18.6 \| 趋势:17.3 | HK core \| HK main board equity + shortsell eligible \| real-data@2026-03-03 \| close=25.44 \| target=38.02 \| fv_source=target_mean_price \| upside=49.5% |
| 4 | BBY | Best Buy | Consumer Cyclical | 81.64 | 风控:17.6 \| 趋势:16.5 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=65.20 \| target=77.37 \| fv_source=target_mean_price \| upside=18.7% |
| 5 | HPE | Hewlett Packard Enterprise | Technology | 77.83 | 风控:16.9 \| 安全边际:16.0 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=21.40 \| target=26.01 \| fv_source=target_mean_price \| upside=21.5% |

## 5) 行业分散约束版 TOP10（单行业最多 2 个）

| 排名 | 代码 | 公司 | 行业 | 组合分 | 最匹配方法论 | 理由 | 备注 |
|---|---|---|---|---:|---|---|---|
| 1 | HPE | Hewlett Packard Enterprise | Technology | 70.77 | 宏观周期 | 催化:19.0 \| 风控:16.0 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=21.40 \| target=26.01 \| fv_source=target_mean_price \| upside=21.5% |
| 2 | 000002.SZ | 万科A | Real Estate | 62.80 | 宏观周期 | 趋势:23.8 \| 催化:16.7 | A core \| CSI300 constituent \| weight=0.128% \| real-data@2026-03-03 \| close=4.67 \| target=5.30 \| fv_source=target_mean_price \| upside=13.4% |
| 3 | CARR | Carrier Global | Industrials | 62.68 | 宏观周期 | 催化:17.8 \| 风控:14.8 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=61.38 \| target=71.80 \| fv_source=target_mean_price \| upside=17.0% |
| 4 | HPQ | HP Inc. | Technology | 58.91 | 宏观周期 | 趋势:23.4 \| 催化:22.7 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=18.73 \| target=19.99 \| fv_source=target_mean_price \| upside=6.8% |
| 5 | BBY | Best Buy | Consumer Cyclical | 57.32 | 宏观周期 | 趋势:20.8 \| 催化:20.4 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=65.20 \| target=77.37 \| fv_source=target_mean_price \| upside=18.7% |
| 6 | 603260.SS | 合盛硅业 | Basic Materials | 54.46 | 宏观周期 | 催化:25.2 \| 趋势:18.8 | A core \| CSI300 constituent \| weight=0.071% \| real-data@2026-03-03 \| close=48.97 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |
| 7 | LEN | Lennar | Consumer Cyclical | 53.86 | 宏观周期 | 催化:25.3 \| 趋势:20.9 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=107.47 \| target=108.62 \| fv_source=target_mean_price \| upside=1.1% |
| 8 | CPB | Campbell's Company (The) | Consumer Defensive | 49.68 | 宏观周期 | 趋势:21.7 \| 催化:19.5 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=26.05 \| target=31.06 \| fv_source=target_mean_price \| upside=19.2% |
| 9 | KHC | Kraft Heinz | Consumer Defensive | 49.08 | 宏观周期 | 催化:24.6 \| 趋势:19.6 | US core \| S&P500 constituent \| real-data@2026-03-03 \| close=24.16 \| target=25.13 \| fv_source=target_mean_price \| upside=4.0% |
| 10 | 601618.SS | 中国中冶 | Industrials | 48.89 | 宏观周期 | 催化:25.0 \| 趋势:14.5 | A core \| CSI300 constituent \| weight=0.089% \| real-data@2026-03-03 \| close=3.12 \| target=NA(fallback-close) \| fv_source=close_fallback \| upside=0.0% |

## 6) 安全边际口径参照

- 项目主口径：`MOS_FV = (FV - P) / FV = 1 - P/FV`（分母为 FV，保留负值）。
- 常见目标价口径：`UPSIDE_P = (FV - P) / P = FV/P - 1`（分母为现价 P）。
- 口径换算：`UPSIDE_P = MOS_FV / (1 - MOS_FV)`；`MOS_FV = UPSIDE_P / (1 + UPSIDE_P)`。
- Yahoo 参照：页面常见 `1y Target Est`（分析师一年目标价），通常按 `UPSIDE_P` 解读。
- Morningstar 参照：常见 `Price/Fair Value`；折价口径可写为 `1 - Price/Fair Value`。
- 详细来源与说明：`docs/margin_of_safety_references.md`。