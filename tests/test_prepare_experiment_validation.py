from __future__ import annotations

import unittest

from scripts.prepare_experiment_validation import build_payload


class PrepareExperimentValidationTests(unittest.TestCase):
    def test_build_payload_selects_shadow_build_experiment(self) -> None:
        issue_context = {
            "number": 22,
            "title": "Monthly Optimization Tasks · CryptoSnapshotPipelines",
            "body": """# Monthly Optimization Tasks · CryptoSnapshotPipelines

## Actions
- [ ] `low` Run monthly shadow build and archive challenger summaries [auto-pr-safe, experiment-only]
  - Summary: Generate official_baseline and challenger_topk_60 coverage each month.
  - Source: [QuantStrategyLab/CryptoSnapshotPipelines #11](https://example.com/11)
- [ ] `low` Document and verify tie-breaking for equal scores [auto-pr-safe]
  - Summary: Confirm deterministic secondary sorting.
  - Source: [QuantStrategyLab/CryptoSnapshotPipelines #11](https://example.com/11)
""",
        }

        payload = build_payload(issue_context)

        self.assertTrue(payload["should_run"])
        self.assertEqual(payload["experiment_task_count"], 1)
        self.assertTrue(payload["run_shadow_build"])
        self.assertFalse(payload["run_walkforward_validation"])

    def test_build_payload_skips_when_no_experiment_tasks_exist(self) -> None:
        issue_context = {
            "number": 30,
            "title": "Monthly Optimization Tasks · CryptoSnapshotPipelines",
            "body": """# Monthly Optimization Tasks · CryptoSnapshotPipelines

## Actions
- [ ] `low` Document and verify tie-breaking for equal scores [auto-pr-safe]
  - Summary: Confirm deterministic secondary sorting.
  - Source: [QuantStrategyLab/CryptoSnapshotPipelines #11](https://example.com/11)
""",
        }

        payload = build_payload(issue_context)

        self.assertFalse(payload["should_run"])
        self.assertEqual(payload["experiment_task_count"], 0)
        self.assertIn("No experiment-only tasks", payload["skip_reason"])


if __name__ == "__main__":
    unittest.main()
