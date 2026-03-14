from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_KPI_LATEST = Path('requirement_ops_custom_kpi_latest.json')
PROJECT_WRITEBACK_LATEST = Path('requirement_ops_project_writeback_latest.json')
PROJECT_WRITEBACK_STATE = Path('requirement_ops_project_writeback_state.json')
PROJECT_WRITEBACK_SCRIPT = Path('/Users/lucas/codex-project/scripts/project_management_writeback.py')

BUSINESS_KPI_IDS = [
    'BIZ-HITZONE-FOCUS-CORE-DATA-COVERAGE',
    'BIZ-HITZONE-SIGNAL-CORE-DATA-COVERAGE',
    'BIZ-HITZONE-TOP50-CORE-DATA-COVERAGE',
    'BIZ-HITZONE-SIGNAL-FORMAL-COVERAGE',
    'BIZ-HITZONE-SIGNAL-FORMAL-OR-REFERENCE-COVERAGE',
    'BIZ-HITZONE-FOCUS-FORMAL-COVERAGE',
    'BIZ-HITZONE-ACTIVE-REVIEW-COVERAGE',
    'BIZ-HITZONE-REVIEW-WRITEBACK-CLOSURE',
]


def normalize_text(value: Any) -> str:
    return str(value or '').strip()


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).astimezone().isoformat()


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if default is None:
        default = {}
    if not path.exists():
        return dict(default)
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return dict(default)
    return payload if isinstance(payload, dict) else dict(default)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _active_requirements(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get('requirements') or []
    return [row for row in rows if isinstance(row, dict) and normalize_text(row.get('status')) != 'superseded']


def _find_requirement_refs(payload: dict[str, Any], *keyword_groups: tuple[str, ...]) -> list[str]:
    refs: list[str] = []
    for row in _active_requirements(payload):
        haystack = f"{normalize_text(row.get('title'))} {normalize_text(row.get('body'))}"
        if any(all(keyword in haystack for keyword in group) for group in keyword_groups):
            req_id = normalize_text(row.get('id'))
            if req_id and req_id not in refs:
                refs.append(req_id)
    return refs


def _first_open_task(backlog: dict[str, Any]) -> dict[str, Any] | None:
    for task in backlog.get('tasks') or []:
        if isinstance(task, dict) and normalize_text(task.get('status')) != 'done':
            return task
    return None


def _dedupe_keep_order(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = normalize_text(value)
        if text and text not in result:
            result.append(text)
    return result


def _workspace_output_path(workspace: Path, filename: Path) -> Path:
    return workspace / 'output' / filename.name


def _hit_zone_metrics_context(adapter_payload: dict[str, Any]) -> dict[str, Any]:
    workspace = Path(adapter_payload.get('workspace') or PROJECT_ROOT).resolve()
    valuation = load_json(workspace / 'output' / 'valuation_coverage_latest.json')
    core_data = load_json(workspace / 'output' / 'core_data_coverage_latest.json')
    review = load_json(workspace / 'output' / 'opportunity_review_writeback_latest.json')
    requirements_payload = adapter_payload.get('requirements') if isinstance(adapter_payload.get('requirements'), dict) else {}
    backlog = adapter_payload.get('backlog') if isinstance(adapter_payload.get('backlog'), dict) else {}

    signal_pool = valuation.get('signal_pool') if isinstance(valuation.get('signal_pool'), dict) else {}
    focus_pool = valuation.get('focus_pool') if isinstance(valuation.get('focus_pool'), dict) else {}
    core_focus_pool = core_data.get('focus_pool') if isinstance(core_data.get('focus_pool'), dict) else {}
    core_signal_pool = core_data.get('signal_pool') if isinstance(core_data.get('signal_pool'), dict) else {}
    core_top50_pool = core_data.get('top50_pool') if isinstance(core_data.get('top50_pool'), dict) else {}
    manual_review = valuation.get('manual_review') if isinstance(valuation.get('manual_review'), dict) else {}
    review_summary = review.get('summary') if isinstance(review.get('summary'), dict) else {}

    signal_count = int(signal_pool.get('count') or 0)
    active_signal_reviewed_count = int(manual_review.get('active_signal_reviewed_count') or 0)
    review_rate = active_signal_reviewed_count / signal_count if signal_count else 0.0
    pending_writeback_count = int(review.get('pending_writeback_count') or 0)
    reviewed_items_count = int(review_summary.get('reviewed_items_count') or 0)
    review_writeback_closure = 1.0 if reviewed_items_count <= 0 else max(0.0, 1.0 - pending_writeback_count / reviewed_items_count)

    valuation_refs = _find_requirement_refs(requirements_payload, ('机会包', '估值'), ('估值',))
    core_data_refs = _find_requirement_refs(requirements_payload, ('核心数据', '覆盖'), ('数据库', '沉淀'), ('增量', '沉淀'))
    review_refs = _find_requirement_refs(requirements_payload, ('复核', '回写'), ('backlog', 'KPI'))
    traceability_refs = _find_requirement_refs(requirements_payload, ('来源映射',), ('可信度',))

    first_open_task = _first_open_task(backlog)
    open_task_refs = [normalize_text(first_open_task.get('id'))] if first_open_task else []

    return {
        'workspace': workspace,
        'valuation': valuation,
        'core_data': core_data,
        'review': review,
        'signal_pool': signal_pool,
        'focus_pool': focus_pool,
        'core_focus_pool': core_focus_pool,
        'core_signal_pool': core_signal_pool,
        'core_top50_pool': core_top50_pool,
        'manual_review': manual_review,
        'review_summary': review_summary,
        'review_rate': review_rate,
        'pending_writeback_count': pending_writeback_count,
        'reviewed_items_count': reviewed_items_count,
        'review_writeback_closure': review_writeback_closure,
        'valuation_refs': valuation_refs,
        'core_data_refs': core_data_refs,
        'review_refs': review_refs,
        'traceability_refs': traceability_refs,
        'open_task_refs': open_task_refs,
    }


def build_hit_zone_custom_kpi_output(adapter_payload: dict[str, Any]) -> dict[str, Any]:
    context = _hit_zone_metrics_context(adapter_payload)
    signal_pool = context['signal_pool']
    focus_pool = context['focus_pool']
    core_focus_pool = context['core_focus_pool']
    core_signal_pool = context['core_signal_pool']
    core_top50_pool = context['core_top50_pool']

    focus_core_data_coverage = float(core_focus_pool.get('core_data_coverage_rate') or 0.0)
    signal_core_data_coverage = float(core_signal_pool.get('core_data_coverage_rate') or 0.0)
    top50_core_data_coverage = float(core_top50_pool.get('core_data_coverage_rate') or 0.0)
    formal_signal_coverage = float(signal_pool.get('formal_valuation_coverage_rate') or 0.0)
    formal_or_reference_coverage = float(signal_pool.get('formal_or_reference_coverage_rate') or 0.0)
    focus_formal_coverage = float(focus_pool.get('formal_valuation_coverage_rate') or 0.0)
    review_rate = float(context['review_rate'])
    pending_writeback_count = int(context['pending_writeback_count'])
    review_writeback_closure = float(context['review_writeback_closure'])

    valuation_evidence = _dedupe_keep_order(context['valuation_refs'] + ['output/valuation_coverage_latest.json'])
    core_data_evidence = _dedupe_keep_order(context['core_data_refs'] + ['output/core_data_coverage_latest.json'])
    review_evidence = _dedupe_keep_order(context['review_refs'] + context['open_task_refs'] + ['output/opportunity_review_writeback_latest.json'])
    traceability_evidence = _dedupe_keep_order(context['traceability_refs'] + ['output/valuation_coverage_latest.json'])

    metrics = [
        {
            'id': 'BIZ-HITZONE-FOCUS-CORE-DATA-COVERAGE',
            'layer': 'result',
            'formula': 'focus_pool.core_data_coverage_rate',
            'target': 1.0,
            'current': focus_core_data_coverage,
            'evidence_refs': core_data_evidence,
        },
        {
            'id': 'BIZ-HITZONE-SIGNAL-CORE-DATA-COVERAGE',
            'layer': 'result',
            'formula': 'signal_pool.core_data_coverage_rate',
            'target': 0.9,
            'current': signal_core_data_coverage,
            'evidence_refs': core_data_evidence,
        },
        {
            'id': 'BIZ-HITZONE-TOP50-CORE-DATA-COVERAGE',
            'layer': 'result',
            'formula': 'top50_pool.core_data_coverage_rate',
            'target': 0.8,
            'current': top50_core_data_coverage,
            'evidence_refs': core_data_evidence,
        },
        {
            'id': 'BIZ-HITZONE-SIGNAL-FORMAL-COVERAGE',
            'layer': 'result',
            'formula': 'signal_pool.formal_valuation_coverage_rate',
            'target': 0.8,
            'current': formal_signal_coverage,
            'evidence_refs': valuation_evidence,
        },
        {
            'id': 'BIZ-HITZONE-SIGNAL-FORMAL-OR-REFERENCE-COVERAGE',
            'layer': 'result',
            'formula': 'signal_pool.formal_or_reference_coverage_rate',
            'target': 1.0,
            'current': formal_or_reference_coverage,
            'evidence_refs': traceability_evidence,
        },
        {
            'id': 'BIZ-HITZONE-FOCUS-FORMAL-COVERAGE',
            'layer': 'result',
            'formula': 'focus_pool.formal_valuation_coverage_rate',
            'target': 1.0,
            'current': focus_formal_coverage,
            'evidence_refs': valuation_evidence,
        },
        {
            'id': 'BIZ-HITZONE-ACTIVE-REVIEW-COVERAGE',
            'layer': 'result',
            'formula': 'manual_review.active_signal_reviewed_count / signal_pool.count',
            'target': 0.5,
            'current': review_rate,
            'evidence_refs': review_evidence,
        },
        {
            'id': 'BIZ-HITZONE-REVIEW-WRITEBACK-CLOSURE',
            'layer': 'result',
            'formula': '1 - pending_writeback_count / reviewed_items_count',
            'target': 1.0,
            'current': review_writeback_closure,
            'evidence_refs': review_evidence,
        },
    ]

    if focus_core_data_coverage < 1.0 or signal_core_data_coverage < 0.9:
        headline = '击球区当前主要瓶颈已经切到核心系统数据覆盖度，估值覆盖只能算代理指标。'
    elif formal_signal_coverage < 0.8:
        headline = '击球区当前主要瓶颈仍是活跃信号的正式估值覆盖率。'
    elif review_rate < 0.5:
        headline = '击球区估值覆盖已基本可用，但人工复核回写覆盖仍偏低。'
    elif pending_writeback_count > 0:
        headline = '击球区人工复核已发生，但仍有待回写项未闭环。'
    else:
        headline = '击球区 requirement-ops 业务指标已形成基础闭环。'

    payload = {
        'metrics': metrics,
        'summary_overrides': {
            'headline': headline,
        },
    }
    write_json(_workspace_output_path(context['workspace'], CUSTOM_KPI_LATEST), payload)
    return payload


def _build_writeback_refs(context: dict[str, Any], extra: dict[str, Any]) -> tuple[list[str], list[str], list[str], list[str]]:
    requirement_refs = _dedupe_keep_order(context['valuation_refs'] + context['core_data_refs'] + context['review_refs'] + context['traceability_refs'])
    task_refs = _dedupe_keep_order(context['open_task_refs'] + [normalize_text(extra.get('task_id'))])
    change_refs = _dedupe_keep_order([str(item) for item in (extra.get('ingested_change_ids') or [])])
    evidence_refs = _dedupe_keep_order(
        requirement_refs
        + task_refs
        + change_refs
        + BUSINESS_KPI_IDS
        + ['output/core_data_coverage_latest.json', 'output/valuation_coverage_latest.json', 'output/opportunity_review_writeback_latest.json']
    )
    return requirement_refs, task_refs, change_refs, evidence_refs


def _build_event_key(hook: str, extra: dict[str, Any]) -> str:
    if hook == 'after_task_update':
        return ':'.join(
            [
                'after_task_update',
                normalize_text(extra.get('task_id')) or 'task',
                normalize_text(extra.get('task_status')) or 'updated',
                normalize_text(extra.get('validation_status')) or 'not_run',
            ]
        )
    change_ids = _dedupe_keep_order([str(item) for item in (extra.get('ingested_change_ids') or [])])
    if change_ids:
        return 'after_cycle:' + ','.join(change_ids)
    return normalize_text(hook) or 'event'


def _payload_fingerprint(payload: dict[str, Any]) -> str:
    digest_payload = {
        'project': payload.get('project'),
        'title': payload.get('title'),
        'summary': payload.get('summary'),
        'verification': payload.get('verification'),
        'next_step': payload.get('next_step'),
        'progress': payload.get('progress'),
        'evidence_refs': payload.get('evidence_refs') or [],
        'requirement_refs': payload.get('requirement_refs') or [],
        'task_refs': payload.get('task_refs') or [],
        'change_refs': payload.get('change_refs') or [],
    }
    body = json.dumps(digest_payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def build_hit_zone_project_writeback_payload(adapter_payload: dict[str, Any]) -> dict[str, Any]:
    hook = normalize_text(adapter_payload.get('hook'))
    extra = adapter_payload.get('extra') if isinstance(adapter_payload.get('extra'), dict) else {}
    workspace = Path(adapter_payload.get('workspace') or PROJECT_ROOT).resolve()
    requirements_payload = adapter_payload.get('requirements') if isinstance(adapter_payload.get('requirements'), dict) else {}
    effective_payload = adapter_payload.get('effective_requirements') if isinstance(adapter_payload.get('effective_requirements'), dict) else {}
    backlog = adapter_payload.get('backlog') if isinstance(adapter_payload.get('backlog'), dict) else {}
    kpi_snapshot = adapter_payload.get('kpi_snapshot') if isinstance(adapter_payload.get('kpi_snapshot'), dict) else {}

    if hook == 'after_cycle' and not (extra.get('ingested_change_ids') or []):
        return {'skipped': True, 'reason': 'no_new_change_ids'}

    context = _hit_zone_metrics_context(adapter_payload)
    active_requirements = _active_requirements(requirements_payload)
    first_open_task = _first_open_task(backlog)
    task_label = ''
    if first_open_task:
        task_label = f"{normalize_text(first_open_task.get('id'))} {normalize_text(first_open_task.get('title'))}".strip()

    signal_pool = context['signal_pool']
    core_focus_pool = context['core_focus_pool']
    core_signal_pool = context['core_signal_pool']
    core_top50_pool = context['core_top50_pool']
    focus_core_data_coverage = float(core_focus_pool.get('core_data_coverage_rate') or 0.0)
    signal_core_data_coverage = float(core_signal_pool.get('core_data_coverage_rate') or 0.0)
    top50_core_data_coverage = float(core_top50_pool.get('core_data_coverage_rate') or 0.0)
    formal_signal_coverage = float(signal_pool.get('formal_valuation_coverage_rate') or 0.0)
    review_rate = float(context['review_rate'])
    pending_writeback_count = int(context['pending_writeback_count'])
    review_writeback_closure = float(context['review_writeback_closure'])
    summary_block = kpi_snapshot.get('summary') if isinstance(kpi_snapshot.get('summary'), dict) else {}

    if hook == 'after_task_update':
        task_id = normalize_text(extra.get('task_id'))
        task_status = normalize_text(extra.get('task_status')) or 'updated'
        title = f"requirement-ops 任务回写：{task_id} {task_status}".strip()
    else:
        change_ids = _dedupe_keep_order([str(item) for item in (extra.get('ingested_change_ids') or [])])
        title = f"requirement-ops 周期回写：{change_ids[-1]}" if change_ids else 'requirement-ops 周期回写'

    summary = (
        f"击球区 requirement-ops 当前正式需求 {len(active_requirements)} 条、生效需求 {len(effective_payload.get('requirements') or [])} 条、"
        f"迭代 {len(backlog.get('iterations') or [])} 个、任务 {len(backlog.get('tasks') or [])} 个；"
        f"核心数据覆盖度 focus={focus_core_data_coverage:.1%}、signal={signal_core_data_coverage:.1%}、top50={top50_core_data_coverage:.1%}；"
        f"活跃信号正式估值覆盖率 {formal_signal_coverage:.1%}，人工复核覆盖率 {review_rate:.1%}，"
        f"回写闭环率 {review_writeback_closure:.1%}，待回写 {pending_writeback_count} 条。"
    )
    verification = (
        f"流程状态={normalize_text(summary_block.get('flow_status')) or 'warn'}，结果状态={normalize_text(summary_block.get('result_status')) or 'warn'}；"
        f"headline={normalize_text(summary_block.get('headline')) or '待补'}；"
        f"证据=output/core_data_coverage_latest.json, output/valuation_coverage_latest.json, output/opportunity_review_writeback_latest.json。"
    )
    next_step = f"优先推进 {task_label}" if task_label else '继续观察下一轮真实产物，并提出新的稳定需求。'
    progress = 'done' if normalize_text(summary_block.get('result_status')) == 'good' else 'building'
    requirement_refs, task_refs, change_refs, evidence_refs = _build_writeback_refs(context, extra)
    event_key = _build_event_key(hook, extra)

    payload = {
        'project': '击球区',
        'hook': hook,
        'event_key': event_key,
        'title': title,
        'summary': summary,
        'verification': verification,
        'next_step': next_step,
        'progress': progress,
        'source': 'requirement-ops-adapter',
        'event_source': 'requirement_ops_adapter',
        'workspace': str(workspace),
        'requirement_refs': requirement_refs,
        'task_refs': task_refs,
        'change_refs': change_refs,
        'kpi_refs': list(BUSINESS_KPI_IDS),
        'evidence_refs': evidence_refs,
    }
    payload['fingerprint'] = _payload_fingerprint(payload)
    write_json(_workspace_output_path(workspace, PROJECT_WRITEBACK_LATEST), payload)
    return payload


def _extract_last_json_object(stdout: str) -> dict[str, Any]:
    text = normalize_text(stdout)
    if not text:
        return {}
    positions = [idx for idx, char in enumerate(text) if char == '{']
    for idx in reversed(positions):
        candidate = text[idx:]
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _load_writeback_state(workspace: Path) -> dict[str, Any]:
    return load_json(_workspace_output_path(workspace, PROJECT_WRITEBACK_STATE))


def _save_writeback_state(workspace: Path, payload: dict[str, Any]) -> None:
    write_json(_workspace_output_path(workspace, PROJECT_WRITEBACK_STATE), payload)


def execute_hit_zone_project_writeback(adapter_payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    payload = build_hit_zone_project_writeback_payload(adapter_payload)
    if payload.get('skipped'):
        return payload

    workspace = Path(payload.get('workspace') or PROJECT_ROOT).resolve()
    state = _load_writeback_state(workspace)
    force_writeback = bool(((adapter_payload.get('extra') if isinstance(adapter_payload.get('extra'), dict) else {}) or {}).get('force_writeback'))
    if not force_writeback and state.get('last_fingerprint') == payload.get('fingerprint'):
        skipped = {
            **payload,
            'skipped': True,
            'reason': 'duplicate_writeback',
            'last_sent_at': normalize_text(state.get('last_sent_at')),
            'last_receipt': state.get('last_receipt') if isinstance(state.get('last_receipt'), dict) else {},
        }
        write_json(_workspace_output_path(workspace, PROJECT_WRITEBACK_LATEST), skipped)
        return skipped

    if dry_run:
        result = {**payload, 'dry_run': True}
        write_json(_workspace_output_path(workspace, PROJECT_WRITEBACK_LATEST), result)
        return result

    command = [
        sys.executable,
        str(PROJECT_WRITEBACK_SCRIPT),
        '--project',
        payload['project'],
        '--title',
        payload['title'],
        '--summary',
        payload['summary'],
        '--verification',
        payload['verification'],
        '--next-step',
        payload['next_step'],
        '--progress',
        payload['progress'],
        '--source',
        payload['source'],
        '--event-source',
        payload['event_source'],
    ]
    proc = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    receipt = _extract_last_json_object(proc.stdout or '')
    result = {
        **payload,
        'returncode': proc.returncode,
        'writeback_receipt': receipt,
        'stdout_tail': '' if receipt else (proc.stdout or '').strip()[-800:],
        'stderr': (proc.stderr or '').strip()[-2000:],
    }
    if proc.returncode != 0:
        raise RuntimeError(f"project_writeback_failed:{proc.returncode}:{result['stderr'] or result['stdout_tail']}")

    _save_writeback_state(
        workspace,
        {
            'last_sent_at': _now_iso(),
            'last_event_key': payload.get('event_key') or '',
            'last_fingerprint': payload.get('fingerprint') or '',
            'last_title': payload.get('title') or '',
            'last_receipt': receipt,
        },
    )
    write_json(_workspace_output_path(workspace, PROJECT_WRITEBACK_LATEST), result)
    return result
