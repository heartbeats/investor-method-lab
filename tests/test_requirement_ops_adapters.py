from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from investor_method_lab.requirement_ops_adapters import (
    PROJECT_WRITEBACK_STATE,
    build_hit_zone_custom_kpi_output,
    build_hit_zone_project_writeback_payload,
    execute_hit_zone_project_writeback,
    write_json,
)


class RequirementOpsAdapterTests(unittest.TestCase):
    def _workspace_payload(self, workspace: Path, *, hook: str = 'score_kpi', extra: dict | None = None) -> dict:
        output_dir = workspace / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / 'valuation_coverage_latest.json',
            {
                'signal_pool': {
                    'count': 20,
                    'formal_valuation_coverage_rate': 0.75,
                    'formal_or_reference_coverage_rate': 1.0,
                },
                'focus_pool': {
                    'formal_valuation_coverage_rate': 1.0,
                },
                'manual_review': {
                    'active_signal_reviewed_count': 4,
                },
            },
        )
        write_json(
            output_dir / 'opportunity_review_writeback_latest.json',
            {
                'summary': {'reviewed_items_count': 4},
                'pending_writeback_count': 1,
            },
        )
        return {
            'workspace': str(workspace),
            'hook': hook,
            'requirements': {
                'requirements': [
                    {'id': 'REQ-0002', 'title': '机会包与估值联动', 'body': '需要把机会包和估值联动起来', 'status': 'active'},
                    {'id': 'REQ-0003', 'title': '来源映射与可信度评分', 'body': '补齐来源映射与可信度评分', 'status': 'active'},
                    {'id': 'REQ-0004', 'title': '人工复核结果回写到 backlog、机会包和 KPI', 'body': '人工复核结果需要回写', 'status': 'active'},
                ]
            },
            'effective_requirements': {'requirements': [{'requirement_id': 'REQ-0002'}, {'requirement_id': 'REQ-0003'}, {'requirement_id': 'REQ-0004'}]},
            'backlog': {
                'iterations': [{'id': 'ITER-0004', 'status': 'doing'}],
                'tasks': [
                    {'id': 'TASK-0010', 'title': '定义集成映射', 'status': 'done'},
                    {'id': 'TASK-0011', 'title': '实现同步链路', 'status': 'doing'},
                ],
            },
            'kpi_snapshot': {'summary': {'flow_status': 'good', 'result_status': 'bad', 'headline': '流程已跑通，但业务闭环未完成。'}},
            'extra': extra or {},
        }

    def test_custom_kpi_adapter_builds_business_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._workspace_payload(Path(tmp))
            result = build_hit_zone_custom_kpi_output(payload)
            metric_ids = [item['id'] for item in result['metrics']]
            self.assertIn('BIZ-HITZONE-SIGNAL-FORMAL-COVERAGE', metric_ids)
            self.assertIn('BIZ-HITZONE-ACTIVE-REVIEW-COVERAGE', metric_ids)
            self.assertIn('BIZ-HITZONE-REVIEW-WRITEBACK-CLOSURE', metric_ids)
            self.assertIn('估值覆盖', result['summary_overrides']['headline'])

    def test_project_writeback_payload_skips_empty_after_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._workspace_payload(Path(tmp), hook='after_cycle', extra={'ingested_change_ids': []})
            result = build_hit_zone_project_writeback_payload(payload)
            self.assertTrue(result['skipped'])
            self.assertEqual(result['reason'], 'no_new_change_ids')

    def test_project_writeback_payload_contains_traceability_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._workspace_payload(Path(tmp), hook='after_task_update', extra={'task_id': 'TASK-0011', 'task_status': 'doing'})
            result = build_hit_zone_project_writeback_payload(payload)
            self.assertEqual(result['project'], '击球区')
            self.assertIn('估值覆盖率', result['summary'])
            self.assertIn('回写闭环率', result['summary'])
            self.assertIn('TASK-0011', result['task_refs'])
            self.assertIn('REQ-0004', result['requirement_refs'])
            self.assertIn('BIZ-HITZONE-ACTIVE-REVIEW-COVERAGE', result['kpi_refs'])
            self.assertTrue(result['fingerprint'])

    def test_project_writeback_dedup_skips_same_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = self._workspace_payload(workspace, hook='after_task_update', extra={'task_id': 'TASK-0011', 'task_status': 'doing'})
            first = build_hit_zone_project_writeback_payload(payload)
            write_json(
                workspace / 'output' / PROJECT_WRITEBACK_STATE.name,
                {
                    'last_sent_at': '2026-03-13T00:00:00+08:00',
                    'last_event_key': first['event_key'],
                    'last_fingerprint': first['fingerprint'],
                    'last_title': first['title'],
                    'last_receipt': {'ok': True},
                },
            )
            result = execute_hit_zone_project_writeback(payload, dry_run=False)
            self.assertTrue(result['skipped'])
            self.assertEqual(result['reason'], 'duplicate_writeback')


if __name__ == '__main__':
    unittest.main()
