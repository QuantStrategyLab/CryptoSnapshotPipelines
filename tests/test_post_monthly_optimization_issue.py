from __future__ import annotations

import unittest

from scripts.post_monthly_optimization_issue import build_issue_body, build_issue_title, build_marker


class PostMonthlyOptimizationIssueTests(unittest.TestCase):
    def test_build_title_and_marker_use_source_reviews(self) -> None:
        plan = {
            "source_reviews": [
                {"source_repo": "QuantStrategyLab/CryptoSnapshotPipelines", "source_issue": {"number": 11, "title": "Monthly Report Review: 2026-04-01"}},
                {"source_repo": "QuantStrategyLab/BinancePlatform", "source_issue": {"number": 9, "title": "Monthly Execution Review: 2026-03"}},
            ]
        }

        self.assertEqual(build_marker(plan), "<!-- monthly-optimization-plan:QuantStrategyLab/CryptoSnapshotPipelines#11|QuantStrategyLab/BinancePlatform#9 -->")
        self.assertEqual(build_issue_title(plan), "Monthly Optimization Plan: 2026-04-01 / 2026-03")

    def test_build_issue_body_prefixes_marker(self) -> None:
        plan = {
            "source_reviews": [
                {"source_repo": "QuantStrategyLab/CryptoSnapshotPipelines", "source_issue": {"number": 11, "title": "Monthly Report Review: 2026-04-01"}}
            ]
        }

        body = build_issue_body(plan, "# Monthly Optimization Planner\n")

        self.assertTrue(body.startswith("<!-- monthly-optimization-plan:"))
        self.assertIn("# Monthly Optimization Planner", body)


if __name__ == "__main__":
    unittest.main()
