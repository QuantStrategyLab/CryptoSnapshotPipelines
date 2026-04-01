from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.prepare_auto_optimization_pr import build_payload, parse_actions, render_pr_body


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PrepareAutoOptimizationPrTests(unittest.TestCase):
    def setUp(self) -> None:
        self.issue_context = {
            "number": 22,
            "title": "Monthly Optimization Tasks · CryptoLeaderRotation: 2026-04-01 / 2026-03",
            "body": """# Monthly Optimization Tasks · CryptoLeaderRotation

## Actions
- [ ] `low` Restore monthly shadow/challenger build generation before review [auto-pr-safe]
  - Summary: Ensure `official_baseline` and `challenger_topk_60` are produced each month.
  - Source: [QuantStrategyLab/CryptoLeaderRotation #11](https://github.com/QuantStrategyLab/CryptoLeaderRotation/issues/11)
- [ ] `low` Document and verify tie-breaking for equal scores [auto-pr-safe]
  - Summary: Confirm the secondary sort used for equal scores is deterministic, stable, and documented.
  - Source: [QuantStrategyLab/CryptoLeaderRotation #11](https://github.com/QuantStrategyLab/CryptoLeaderRotation/issues/11)
- [ ] `low` Add a boundary tracker [auto-pr-safe, experiment-only]
  - Summary: Track near-cutoff symbols monthly.
  - Source: [QuantStrategyLab/CryptoLeaderRotation #11](https://github.com/QuantStrategyLab/CryptoLeaderRotation/issues/11)
""",
        }

    def test_parse_actions_preserves_risk_flags_and_source(self) -> None:
        actions = parse_actions(self.issue_context["body"])

        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[0]["risk_level"], "low")
        self.assertEqual(actions[0]["flags"], ["auto-pr-safe"])
        self.assertEqual(actions[2]["flags"], ["auto-pr-safe", "experiment-only"])
        self.assertEqual(actions[2]["source_label"], "QuantStrategyLab/CryptoLeaderRotation #11")

    def test_build_payload_skips_completed_clr_tasks_and_excludes_experiments(self) -> None:
        payload = build_payload(self.issue_context, repo_root=PROJECT_ROOT)

        self.assertFalse(payload["should_run"])
        self.assertEqual(payload["safe_task_count"], 0)
        self.assertEqual(payload["skipped_task_count"], 2)
        self.assertEqual(
            [action["title"] for action in payload["skipped_actions"]],
            [
                "Restore monthly shadow/challenger build generation before review",
                "Document and verify tie-breaking for equal scores",
            ],
        )

    def test_render_pr_body_contains_marker_and_issue_reference(self) -> None:
        issue_context = {
            "number": 30,
            "title": "Monthly Optimization Tasks · Sandbox",
            "body": """# Monthly Optimization Tasks · Sandbox

## Actions
- [ ] `low` Add a short README note [auto-pr-safe]
  - Summary: Document a small operator-facing behavior.
  - Source: [Sandbox #1](https://example.com/issues/1)
""",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = build_payload(issue_context, repo_root=Path(temp_dir))
        body = render_pr_body(payload)

        self.assertIn("<!-- auto-optimization-pr:issue-30 -->", body)
        self.assertIn("Add a short README note", body)
        self.assertIn("Refs #30", body)


if __name__ == "__main__":
    unittest.main()
