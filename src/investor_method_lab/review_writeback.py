from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from investor_method_lab.signal_ledger import normalize_text, ticker_lookup_keys

MANUAL_DECISION_DEFAULT_ACTION = {
    "通过": "promote_to_pack",
    "观察": "keep_in_watch_pool",
    "驳回": "archive",
    "升级": "upgrade_valuation_source",
}
ACTION_LABELS = {
    "promote_to_pack": "纳入机会包",
    "keep_in_watch_pool": "保留观察",
    "archive": "归档",
    "upgrade_valuation_source": "补估值源",
    "manual_escalation": "升级复核",
}
FOLLOWUP_ACTIONS = {"promote_to_pack", "upgrade_valuation_source", "manual_escalation"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()



def _parse_datetime(value: Any) -> datetime | None:
    text = normalize_text(value)
    if not text:
        return None
    candidates = [text]
    if len(text) == 10 and text.count("-") == 2:
        candidates.append(f"{text}T00:00:00+00:00")
    for item in candidates:
        try:
            return datetime.fromisoformat(item.replace("Z", "+00:00"))
        except ValueError:
            continue
    return None



def _sort_datetime_key(value: Any) -> tuple[int, str]:
    dt = _parse_datetime(value)
    if dt is None:
        return (0, "")
    return (1, dt.isoformat())



def ticker_key(value: Any) -> str:
    return normalize_text(value).upper()



def action_label(action: Any) -> str:
    return ACTION_LABELS.get(normalize_text(action), normalize_text(action))



def format_manual_review_summary(item: Dict[str, Any]) -> str:
    decision = normalize_text(item.get("manual_review_decision"))
    action = normalize_text(item.get("manual_action"))
    note = normalize_text(item.get("manual_note"))
    parts: List[str] = []
    if decision:
        parts.append(f"人工{decision}")
    if action:
        parts.append(action_label(action))
    if note:
        parts.append(note)
    return " | ".join(parts)



def load_review_writeback(path: Path | None) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))



def reviewed_items(payload: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("reviewed_items") or []
    return [dict(item) for item in rows if isinstance(item, dict)]



def reviewed_items_by_ticker(payload: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    for item in reviewed_items(payload):
        ticker = ticker_key(item.get("ticker"))
        if not ticker:
            continue
        previous = mapping.get(ticker)
        if previous is None or _sort_datetime_key(item.get("manual_reviewed_at")) >= _sort_datetime_key(previous.get("manual_reviewed_at")):
            mapping[ticker] = item
    return mapping



def build_backlog_items(reviewed: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in reviewed:
        decision = normalize_text(item.get("manual_review_decision"))
        action = normalize_text(item.get("manual_action"))
        if action not in FOLLOWUP_ACTIONS:
            continue
        signal_id = normalize_text(item.get("signal_id"))
        ticker = normalize_text(item.get("ticker"))
        name = normalize_text(item.get("name")) or ticker or signal_id
        title_action = action_label(action)
        rows.append(
            {
                "id": f"RWB-{signal_id or ticker or len(rows) + 1}",
                "signal_id": signal_id,
                "ticker": ticker,
                "name": name,
                "priority": normalize_text(item.get("priority")) or "P2",
                "decision": decision,
                "action": action,
                "action_label": title_action,
                "title": f"{name}：{title_action}",
                "objective": normalize_text(item.get("manual_note")) or f"根据人工复核结论“{decision or action}”，执行后续动作：{title_action}。",
                "source": "feishu_review_queue_manual",
                "status": "todo",
                "manual_reviewed_at": normalize_text(item.get("manual_reviewed_at")),
                "writeback_status": normalize_text(item.get("writeback_status")) or "pending",
            }
        )
    rows.sort(key=lambda row: (normalize_text(row.get("priority")), normalize_text(row.get("ticker"))))
    return rows



def summarize_review_writeback(reviewed: Sequence[Dict[str, Any]], backlog: Sequence[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    backlog = list(backlog or build_backlog_items(reviewed))
    decision_breakdown: Dict[str, int] = {}
    action_breakdown: Dict[str, int] = {}
    writeback_status_breakdown: Dict[str, int] = {}
    for item in reviewed:
        decision = normalize_text(item.get("manual_review_decision")) or "unknown"
        action = normalize_text(item.get("manual_action")) or MANUAL_DECISION_DEFAULT_ACTION.get(decision, "unknown")
        status = normalize_text(item.get("writeback_status")) or "pending"
        decision_breakdown[decision] = decision_breakdown.get(decision, 0) + 1
        action_breakdown[action] = action_breakdown.get(action, 0) + 1
        writeback_status_breakdown[status] = writeback_status_breakdown.get(status, 0) + 1
    return {
        "reviewed_items_count": len(reviewed),
        "followup_backlog_count": len(backlog),
        "decision_breakdown": decision_breakdown,
        "action_breakdown": action_breakdown,
        "writeback_status_breakdown": writeback_status_breakdown,
        "generated_at_utc": _now_iso(),
    }



def render_review_writeback_markdown(payload: Dict[str, Any]) -> str:
    reviewed = reviewed_items(payload)
    backlog = [dict(item) for item in (payload.get("backlog_items") or []) if isinstance(item, dict)]
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else summarize_review_writeback(reviewed, backlog)

    lines: List[str] = []
    lines.append("# 机会复核回写最新快照")
    lines.append("")
    lines.append(f"- 生成时间：{normalize_text(payload.get('generated_at_utc')) or normalize_text(summary.get('generated_at_utc'))}")
    lines.append(f"- 已人工复核：{int(summary.get('reviewed_items_count') or 0)}")
    lines.append(f"- 需继续跟进：{int(summary.get('followup_backlog_count') or 0)}")
    lines.append("")
    lines.append("## 人工结论")
    lines.append("")
    lines.append(json.dumps(summary.get("decision_breakdown") or {}, ensure_ascii=False))
    lines.append("")
    lines.append("## 后续动作")
    lines.append("")
    lines.append(json.dumps(summary.get("action_breakdown") or {}, ensure_ascii=False))
    lines.append("")
    lines.append("## 待跟进 Backlog")
    lines.append("")
    lines.append("| 标的 | 优先级 | 动作 | 目标 |")
    lines.append("|---|---|---|---|")
    for item in backlog:
        lines.append(
            f"| {normalize_text(item.get('name'))}({normalize_text(item.get('ticker'))}) | {normalize_text(item.get('priority')) or '-'} | {normalize_text(item.get('action_label')) or '-'} | {normalize_text(item.get('objective')) or '-'} |"
        )
    if not backlog:
        lines.append("| - | - | - | 当前无新增待跟进动作 |")
    lines.append("")
    lines.append("## 最近人工复核")
    lines.append("")
    lines.append("| 标的 | 结论 | 动作 | 备注 |")
    lines.append("|---|---|---|---|")
    for item in reviewed[:20]:
        lines.append(
            f"| {normalize_text(item.get('name'))}({normalize_text(item.get('ticker'))}) | {normalize_text(item.get('manual_review_decision')) or '-'} | {action_label(item.get('manual_action')) or '-'} | {normalize_text(item.get('manual_note')) or '-'} |"
        )
    if not reviewed:
        lines.append("| - | - | - | 当前还没有人工复核写回 |")
    lines.append("")
    return "\n".join(lines)



def build_review_payload(*, source: Dict[str, Any], reviewed: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    reviewed_rows = [dict(item) for item in reviewed]
    backlog = build_backlog_items(reviewed_rows)
    summary = summarize_review_writeback(reviewed_rows, backlog)
    return {
        "generated_at_utc": _now_iso(),
        "source": source,
        "reviewed_items": reviewed_rows,
        "backlog_items": backlog,
        "summary": summary,
    }



def ticker_aliases(item: Dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for raw in [item.get("ticker"), item.get("name")]:
        for key in ticker_lookup_keys(raw):
            normalized = normalize_text(key).upper()
            if normalized:
                keys.add(normalized)
    return keys
