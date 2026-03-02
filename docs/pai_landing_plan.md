# PAI 思路落地方案（investor-method-lab）

## 1) 目标

把“研究 -> 生成 -> 验证 -> 记录 -> 迭代”做成可重复运行的闭环，避免只靠人工触发和口头同步。

## 2) 从 PAI 借鉴了什么

| PAI 思路 | 本项目落地 |
|---|---|
| 统一执行入口 | `scripts/pai_loop.py` 作为唯一迭代入口，串联核心步骤 |
| 可观测与可审计 | 每轮输出 `report.md`、`latest_manifest.json`、`runs.jsonl` |
| 漂移防护 | 对关键产物做存在性/空文件/Markdown 行数骤降检查 |
| 分层执行 | 默认样例数据路径 + 可选实时数据路径（`--with-real-data`） |
| 失败快速止损 | 任一步骤失败即停止后续步骤，避免放大脏状态 |

## 3) 已落地能力

- 固定执行序列：
  - `build_verified_investors`
  - `generate_top20_pack_sample`
  - `build_real_opportunities`（可选）
  - `generate_top20_pack_real`（可选）
  - `unit_tests`
- 关键产物快照：
  - `data/top20_global_investors_verified_ab.json`
  - `docs/top20_global_investors_verified_ab.md`
  - `docs/top20_verification_backlog.md`
  - `docs/top20_opportunity_pack.md`
  - `output/top20_first_batch_opportunities.csv`
  - `output/top20_methodology_top5_by_group.csv`
  - `output/top20_diversified_opportunities.csv`
- 报告归档目录：
  - `output/pai_loop/<run_id>/report.md`
  - `output/pai_loop/latest_report.md`
  - `output/pai_loop/latest_manifest.json`
  - `output/pai_loop/runs.jsonl`

## 4) 运行方式（可直接执行）

```bash
cd /home/afu/projects/investor-method-lab

# 仅样例数据闭环（非真实数据口径）
python3 scripts/pai_loop.py

# 包含实时数据闭环（Yahoo Finance）
python3 scripts/pai_loop.py --with-real-data

# 只看将执行的步骤，不实际执行
python3 scripts/pai_loop.py --dry-run
```

## 5) 定时执行（cron）

```bash
cd /home/afu/projects/investor-method-lab
bash scripts/install_pai_loop_cron.sh apply
bash scripts/install_pai_loop_cron.sh status
```

默认计划：

- 每天 `09:10` 跑实时数据闭环（仅 `real`，更新真实口径）
- 定时入口统一走 `scripts/pai_loop_guard.sh`，失败自动触发告警逻辑

日志文件：

- `output/pai_loop/cron_real.log`
- `output/pai_loop/alert.log`

飞书告警（可选）：

```bash
cat > .env.pai <<'EOF'
PAI_FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx'
# 或使用 FEISHU_BOT_WEBHOOK_URL 作为兼容变量
# 或复用现有 app 推送环境（默认会尝试读取 ~/.config/dcf_notify.env）
# PAI_NOTIFY_ENV_FILE="$HOME/.config/dcf_notify.env"
# PAI_NOTIFY_ON_SUCCESS=1
EOF
```

说明：

- 未配置 webhook 时，会自动尝试 app 发送脚本（`/home/afu/codex-project/scripts/send_feishu_text_message.py`）。
- 若 webhook 与 app 发送都不可用，不会中断任务，只写 `alert.log`。
- 默认仅失败告警；若需成功也通知，设置 `PAI_NOTIFY_ON_SUCCESS=1`。
- `scripts/pai_loop_guard.sh` 会优先加载项目根目录 `.env.pai`（可通过 `PAI_ENV_FILE` 改路径）。

## 6) 失败与告警处理

1. 先看 `output/pai_loop/latest_report.md` 的失败步骤和告警项。
2. 如果是步骤失败：
   - 先单独复跑失败步骤对应脚本
   - 修复后再重跑 `python3 scripts/pai_loop.py`
3. 如果是漂移告警（如 Markdown 行数异常下降）：
   - 人工核对该文件 diff 是否符合预期
   - 非预期则回滚到上一个可信版本后重跑
4. 连续两轮失败时，暂停 cron 并进入人工排障：
   - `bash scripts/install_pai_loop_cron.sh remove`

## 7) 当前状态（已验证）

- `python3 scripts/pai_loop.py --dry-run`：通过
- `python3 scripts/pai_loop.py`：通过
- `python3 scripts/pai_loop.py --with-real-data`：通过
