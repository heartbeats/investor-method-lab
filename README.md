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

### 价值质量复利（巴芒口径）执行门槛

- 硬门槛：`margin_of_safety >= 15%`，且（有 `certainty_score` 时）`certainty_score >= 65`
- 软惩罚：`margin_of_safety < 30%` 或 `certainty_score < 75` 时下调该策略得分
- 说明：该门槛目前仅作用于 `value_quality_compound` 分组

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

- `data/top20_global_investors_10y_plus_calibrated.json`：Top20 校准版（含可信度与口径）
- `docs/data_calibration_notes_2026-02-27.md`：校准说明与关键修正
- `data/top20_global_investors_verified_ab.json`：可审计版（仅 A/B）
- `docs/top20_global_investors_verified_ab.md`：可审计榜单报告
- `docs/top20_verification_backlog.md`：C 级待核验清单
- `data/top20_global_investors_verified_a_only.json`：最严格版（仅 A）

## 8. PAI 迭代闭环（已落地）

- 核心脚本：`scripts/pai_loop.py`
- 落地说明：`docs/pai_landing_plan.md`
- 定时安装：`scripts/install_pai_loop_cron.sh`

```bash
cd /home/afu/projects/investor-method-lab

# 默认闭环：样例数据路径（非真实数据口径）
python3 scripts/pai_loop.py

# 实时数据闭环：包含 Yahoo Finance 刷新
python3 scripts/pai_loop.py --with-real-data

# 查看计划任务状态 / 安装定时任务
bash scripts/install_pai_loop_cron.sh status
bash scripts/install_pai_loop_cron.sh apply
```

- 闭环报告输出：`output/pai_loop/latest_report.md`
- 历史运行记录：`output/pai_loop/runs.jsonl`
