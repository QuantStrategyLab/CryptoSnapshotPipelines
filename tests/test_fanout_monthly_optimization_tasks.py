from __future__ import annotations

import unittest

from scripts.fanout_monthly_optimization_tasks import (
    build_closed_issue_body,
    build_issue_body,
    build_issue_title,
    build_marker,
)


class FanoutMonthlyOptimizationTasksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = {
            "source_reviews": [
                {
                    "source_repo": "QuantStrategyLab/CryptoLeaderRotation",
                    "source_issue": {"number": 11, "title": "Monthly Report Review: 2026-04-01"},
                },
                {
                    "source_repo": "QuantStrategyLab/BinancePlatform",
                    "source_issue": {"number": 9, "title": "Monthly Execution Review: 2026-03"},
                },
            ],
            "repo_action_summary": {
                "BinancePlatform": {
                    "count": 2,
                    "highest_risk_level": "high",
                    "actions": [
                        {
                            "risk_level": "high",
                            "title": "Reconcile March cash flows",
                            "summary": "Separate withdrawals from mark-to-market moves.",
                            "source_repo": "QuantStrategyLab/BinancePlatform",
                            "source_issue_number": 9,
                            "source_issue_url": "https://github.com/QuantStrategyLab/BinancePlatform/issues/9",
                            "auto_pr_safe": False,
                            "experiment_only": False,
                        },
                        {
                            "risk_level": "low",
                            "title": "Add zero-trade diagnostics",
                            "summary": "Keep gating reasons visible in the report.",
                            "source_repo": "QuantStrategyLab/BinancePlatform",
                            "source_issue_number": 9,
                            "source_issue_url": "https://github.com/QuantStrategyLab/BinancePlatform/issues/9",
                            "auto_pr_safe": True,
                            "experiment_only": False,
                        },
                    ],
                }
            },
        }

    def test_build_marker_and_title_include_owner_repo(self) -> None:
        self.assertEqual(
            build_marker(self.plan, "BinancePlatform"),
            "<!-- monthly-optimization-task:BinancePlatform:QuantStrategyLab/CryptoLeaderRotation#11|QuantStrategyLab/BinancePlatform#9 -->",
        )
        self.assertEqual(
            build_issue_title(self.plan, "BinancePlatform"),
            "Monthly Optimization Tasks · BinancePlatform: 2026-04-01 / 2026-03",
        )

    def test_build_issue_body_lists_repo_specific_actions_and_flags(self) -> None:
        body = build_issue_body(
            self.plan,
            "BinancePlatform",
            planner_issue_url="https://github.com/QuantStrategyLab/CryptoLeaderRotation/issues/20",
        )

        self.assertIn("# Monthly Optimization Tasks · BinancePlatform", body)
        self.assertIn("Planner issue: https://github.com/QuantStrategyLab/CryptoLeaderRotation/issues/20", body)
        self.assertIn("Actions in this repo: `2`", body)
        self.assertIn("Highest repo risk: `high`", body)
        self.assertIn("Reconcile March cash flows", body)
        self.assertIn("Add zero-trade diagnostics [auto-pr-safe]", body)
        self.assertIn("Source: [QuantStrategyLab/BinancePlatform #9]", body)

    def test_build_closed_issue_body_marks_repo_as_resolved(self) -> None:
        body = build_closed_issue_body(
            self.plan,
            "CryptoStrategies",
            planner_issue_url="https://github.com/QuantStrategyLab/CryptoLeaderRotation/issues/20",
        )

        self.assertIn("<!-- monthly-optimization-task:CryptoStrategies:", body)
        self.assertIn("No repo-scoped tasks remain", body)
        self.assertIn("This issue is being closed", body)


if __name__ == "__main__":
    unittest.main()
