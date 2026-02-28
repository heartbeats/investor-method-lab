#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "pai_loop"

# Core artifacts that must remain valid and non-empty.
CRITICAL_ARTIFACTS = [
    PROJECT_ROOT / "data" / "top20_global_investors_verified_ab.json",
    PROJECT_ROOT / "docs" / "top20_global_investors_verified_ab.md",
    PROJECT_ROOT / "docs" / "top20_verification_backlog.md",
    PROJECT_ROOT / "docs" / "top20_opportunity_pack.md",
    PROJECT_ROOT / "output" / "top20_first_batch_opportunities.csv",
    PROJECT_ROOT / "output" / "top20_methodology_top5_by_group.csv",
    PROJECT_ROOT / "output" / "top20_diversified_opportunities.csv",
]

# If a critical markdown file line-count drops below this ratio, mark as drift risk.
LINE_DROP_ALERT_RATIO = 0.60


@dataclass
class StepResult:
    name: str
    cmd: List[str]
    rc: int
    duration_sec: float
    stdout_tail: str
    stderr_tail: str

    @property
    def status(self) -> str:
        return "ok" if self.rc == 0 else "failed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PAI-inspired iterative loop for investor-method-lab")
    parser.add_argument(
        "--with-real-data",
        action="store_true",
        help="Include Yahoo-based real-data refresh and generate real-data pack",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip unit tests",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    return parser.parse_args()


def now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f)


def capture_artifacts(paths: List[Path]) -> Dict[str, Dict[str, Any]]:
    snap: Dict[str, Dict[str, Any]] = {}
    for p in paths:
        rel = str(p.relative_to(PROJECT_ROOT))
        if not p.exists():
            snap[rel] = {
                "exists": False,
                "size": 0,
                "lines": 0,
                "sha256": "",
            }
            continue
        snap[rel] = {
            "exists": True,
            "size": p.stat().st_size,
            "lines": line_count(p),
            "sha256": sha256_of(p),
        }
    return snap


def run_step(name: str, cmd: List[str], dry_run: bool) -> StepResult:
    if dry_run:
        return StepResult(
            name=name,
            cmd=cmd,
            rc=0,
            duration_sec=0.0,
            stdout_tail="DRY-RUN",
            stderr_tail="",
        )

    start = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    duration = time.time() - start
    stdout_tail = "\n".join(proc.stdout.strip().splitlines()[-20:])
    stderr_tail = "\n".join(proc.stderr.strip().splitlines()[-20:])
    return StepResult(
        name=name,
        cmd=cmd,
        rc=proc.returncode,
        duration_sec=duration,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
    )


def build_steps(with_real_data: bool, skip_tests: bool) -> List[tuple[str, List[str]]]:
    steps: List[tuple[str, List[str]]] = [
        (
            "build_verified_investors",
            [sys.executable, "scripts/build_verified_investors.py", "--min-confidence", "B"],
        ),
        (
            "generate_top20_pack_sample",
            [sys.executable, "scripts/generate_top20_opportunity_pack.py"],
        ),
    ]

    if with_real_data:
        steps.extend(
            [
                (
                    "build_real_opportunities",
                    [sys.executable, "scripts/build_real_opportunities.py"],
                ),
                (
                    "generate_top20_pack_real",
                    [
                        sys.executable,
                        "scripts/generate_top20_opportunity_pack.py",
                        "--opportunities-file",
                        str(PROJECT_ROOT / "data" / "opportunities.real.csv"),
                        "--output-csv",
                        str(PROJECT_ROOT / "output" / "top20_first_batch_opportunities_real.csv"),
                        "--output-group-csv",
                        str(PROJECT_ROOT / "output" / "top20_methodology_top5_by_group_real.csv"),
                        "--output-diversified-csv",
                        str(PROJECT_ROOT / "output" / "top20_diversified_opportunities_real.csv"),
                        "--output-md",
                        str(PROJECT_ROOT / "docs" / "top20_opportunity_pack_real.md"),
                    ],
                ),
            ]
        )

    if not skip_tests:
        steps.append(("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]))

    return steps


def detect_drift(
    old_snap: Dict[str, Dict[str, Any]],
    new_snap: Dict[str, Dict[str, Any]],
) -> List[str]:
    alerts: List[str] = []
    for rel, cur in new_snap.items():
        if not cur["exists"]:
            alerts.append(f"{rel}: missing")
            continue
        if cur["size"] <= 0:
            alerts.append(f"{rel}: empty file")
            continue

        prev = old_snap.get(rel)
        if not prev or not prev.get("exists"):
            continue

        # Drift guard for markdown reports: sudden truncation.
        if rel.endswith(".md"):
            prev_lines = int(prev.get("lines", 0))
            cur_lines = int(cur.get("lines", 0))
            if prev_lines > 0 and cur_lines / prev_lines < LINE_DROP_ALERT_RATIO:
                alerts.append(
                    f"{rel}: line count dropped from {prev_lines} to {cur_lines} (<{LINE_DROP_ALERT_RATIO:.2f})"
                )
    return alerts


def render_markdown(
    run_id: str,
    started_at: str,
    with_real_data: bool,
    skip_tests: bool,
    steps: List[StepResult],
    old_snap: Dict[str, Dict[str, Any]],
    new_snap: Dict[str, Dict[str, Any]],
    drift_alerts: List[str],
) -> str:
    lines: List[str] = []
    lines.append("# PAI 迭代闭环报告")
    lines.append("")
    lines.append(f"- run_id: `{run_id}`")
    lines.append(f"- started_at: `{started_at}`")
    lines.append(f"- with_real_data: `{with_real_data}`")
    lines.append(f"- skip_tests: `{skip_tests}`")
    lines.append("")

    lines.append("## 1) 执行步骤")
    lines.append("")
    lines.append("| Step | Status | RC | Duration(s) |")
    lines.append("|---|---|---:|---:|")
    for s in steps:
        lines.append(f"| `{s.name}` | {s.status} | {s.rc} | {s.duration_sec:.2f} |")
    lines.append("")

    lines.append("## 2) 关键产物快照")
    lines.append("")
    lines.append("| Artifact | Exists | Size | Lines | Changed |")
    lines.append("|---|---|---:|---:|---|")
    for rel, cur in new_snap.items():
        old = old_snap.get(rel)
        changed = "yes" if old and old.get("sha256") != cur.get("sha256") else "no"
        lines.append(
            f"| `{rel}` | {cur['exists']} | {cur['size']} | {cur['lines']} | {changed} |"
        )
    lines.append("")

    lines.append("## 3) 漂移与告警")
    lines.append("")
    if drift_alerts:
        for a in drift_alerts:
            lines.append(f"- [ALERT] {a}")
    else:
        lines.append("- 无关键漂移告警。")
    lines.append("")

    lines.append("## 4) 失败步骤日志摘要")
    lines.append("")
    failed = [s for s in steps if s.rc != 0]
    if not failed:
        lines.append("- 无失败步骤。")
    else:
        for s in failed:
            lines.append(f"### {s.name}")
            lines.append("")
            lines.append("```text")
            if s.stdout_tail:
                lines.append("[stdout]")
                lines.append(s.stdout_tail)
            if s.stderr_tail:
                lines.append("[stderr]")
                lines.append(s.stderr_tail)
            lines.append("```")
            lines.append("")

    lines.append("## 5) 下一步建议")
    lines.append("")
    if failed:
        lines.append("- 先修复失败步骤后再执行下一轮，避免脏状态放大。")
    if drift_alerts:
        lines.append("- 对告警文件做人工 diff，确认是否是预期变更。")
    if not failed and not drift_alerts:
        lines.append("- 本轮可进入下一次迭代，继续用同一参数跑增量更新。")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    started_at = now_local()
    run_dir = OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = OUTPUT_DIR / "latest_manifest.json"
    old_snap: Dict[str, Dict[str, Any]] = {}
    if manifest_path.exists():
        old_snap = json.loads(manifest_path.read_text(encoding="utf-8"))

    step_defs = build_steps(with_real_data=args.with_real_data, skip_tests=args.skip_tests)
    step_results: List[StepResult] = []

    for name, cmd in step_defs:
        result = run_step(name=name, cmd=cmd, dry_run=args.dry_run)
        step_results.append(result)
        if result.rc != 0:
            # Stop on first failure to preserve deterministic state.
            break

    new_snap = capture_artifacts(CRITICAL_ARTIFACTS)
    drift_alerts = detect_drift(old_snap=old_snap, new_snap=new_snap)

    report = render_markdown(
        run_id=run_id,
        started_at=started_at,
        with_real_data=args.with_real_data,
        skip_tests=args.skip_tests,
        steps=step_results,
        old_snap=old_snap,
        new_snap=new_snap,
        drift_alerts=drift_alerts,
    )
    report_path = run_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")

    (OUTPUT_DIR / "latest_report.md").write_text(report, encoding="utf-8")
    manifest_path.write_text(json.dumps(new_snap, ensure_ascii=False, indent=2), encoding="utf-8")

    run_record = {
        "run_id": run_id,
        "started_at": started_at,
        "with_real_data": args.with_real_data,
        "skip_tests": args.skip_tests,
        "dry_run": args.dry_run,
        "steps": [
            {
                "name": s.name,
                "cmd": s.cmd,
                "rc": s.rc,
                "duration_sec": round(s.duration_sec, 3),
            }
            for s in step_results
        ],
        "drift_alerts": drift_alerts,
        "report_path": str(report_path.relative_to(PROJECT_ROOT)),
    }
    with (OUTPUT_DIR / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(run_record, ensure_ascii=False) + "\n")

    has_failed_step = any(s.rc != 0 for s in step_results)
    has_alert = len(drift_alerts) > 0

    print(f"[pai-loop] run_id={run_id}")
    print(f"[pai-loop] report={report_path}")
    print(f"[pai-loop] failed_steps={has_failed_step} drift_alerts={len(drift_alerts)}")

    if has_failed_step or has_alert:
        sys.exit(2)


if __name__ == "__main__":
    main()

