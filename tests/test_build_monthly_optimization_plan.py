from __future__ import annotations

import unittest

from scripts.build_monthly_optimization_plan import build_plan, render_summary_markdown


class BuildMonthlyOptimizationPlanTests(unittest.TestCase):
    def test_build_plan_groups_actions_by_owner_repo(self) -> None:
        upstream_review = {
            "source_repo": "QuantStrategyLab/CryptoLeaderRotation",
            "review_kind": "upstream_selector",
            "source_issue": {"number": 11, "title": "Monthly Report Review: 2026-04-01", "url": "https://github.com/a/b/issues/11"},
            "risk_level": "medium",
            "production_recommendation": "research_only",
            "summary": "Need more challenger evidence.",
            "recommended_actions": [
                {
                    "owner_repo": "CryptoLeaderRotation",
                    "title": "Add challenger breadth check",
                    "risk_level": "low",
                    "auto_pr_safe": True,
                    "experiment_only": True,
                    "summary": "Improve evidence coverage.",
                }
            ],
        }
        downstream_review = {
            "source_repo": "QuantStrategyLab/BinancePlatform",
            "review_kind": "execution_runtime",
            "source_issue": {"number": 9, "title": "Monthly Execution Review: 2026-03", "url": "https://github.com/a/b/issues/9"},
            "risk_level": "low",
            "production_recommendation": "keep_production_as_is",
            "summary": "Execution looked healthy.",
            "recommended_actions": [
                {
                    "owner_repo": "BinancePlatform",
                    "title": "Keep gating summary visible",
                    "risk_level": "low",
                    "auto_pr_safe": True,
                    "experiment_only": False,
                    "summary": "No change to production behavior.",
                }
            ],
        }

        plan = build_plan(upstream_review, downstream_review)

        self.assertEqual(plan["highest_review_risk"], "medium")
        self.assertIn("CryptoLeaderRotation", plan["repo_action_summary"])
        self.assertIn("BinancePlatform", plan["repo_action_summary"])
        self.assertEqual(len(plan["safe_auto_pr_candidates"]), 2)
        self.assertEqual(len(plan["experiment_candidates"]), 1)

    def test_build_plan_reassigns_reporting_tasks_and_downgrades_manual_checks(self) -> None:
        upstream_review = {
            "source_repo": "QuantStrategyLab/CryptoLeaderRotation",
            "review_kind": "upstream_selector",
            "source_issue": {"number": 11, "title": "Monthly Report Review: 2026-04-01", "url": "https://github.com/a/b/issues/11"},
            "risk_level": "low",
            "production_recommendation": "keep_production_as_is",
            "summary": "Upstream is stable.",
            "recommended_actions": [],
        }
        downstream_review = {
            "source_repo": "QuantStrategyLab/BinancePlatform",
            "review_kind": "execution_runtime",
            "source_issue": {"number": 9, "title": "Monthly Execution Review: 2026-03", "url": "https://github.com/a/b/issues/9"},
            "risk_level": "medium",
            "production_recommendation": "needs_attention",
            "summary": "Execution needs follow-up.",
            "recommended_actions": [
                {
                    "owner_repo": "CryptoStrategies",
                    "title": "Add monthly report cash-flow attribution",
                    "risk_level": "low",
                    "auto_pr_safe": True,
                    "experiment_only": False,
                    "summary": "Extend the monthly report to show deposits, withdrawals, realized PnL, and unrealized PnL separately.",
                },
                {
                    "owner_repo": "BinancePlatform",
                    "title": "Check DCA and rotation eligibility gates against current free USDT",
                    "risk_level": "low",
                    "auto_pr_safe": True,
                    "experiment_only": False,
                    "summary": "Verify minimum order size, reserve floor, and available balance thresholds.",
                },
            ],
        }

        plan = build_plan(upstream_review, downstream_review)

        bp_actions = plan["repo_action_summary"]["BinancePlatform"]["actions"]
        self.assertEqual([action["title"] for action in bp_actions], [
            "Check DCA and rotation eligibility gates against current free USDT",
            "Add monthly report cash-flow attribution",
        ])
        self.assertEqual(bp_actions[0]["auto_pr_safe"], False)
        self.assertEqual(bp_actions[1]["auto_pr_safe"], True)
        self.assertEqual(len(plan["safe_auto_pr_candidates"]), 1)

    def test_render_summary_markdown_mentions_source_reviews_and_repos(self) -> None:
        plan = {
            "highest_review_risk": "medium",
            "safe_auto_pr_candidates": [{}, {}],
            "experiment_candidates": [{}],
            "human_review_required": [{}],
            "source_reviews": [
                {
                    "source_repo": "QuantStrategyLab/CryptoLeaderRotation",
                    "risk_level": "medium",
                    "production_recommendation": "research_only",
                    "summary": "Need more evidence.",
                    "source_issue": {"title": "Monthly Report Review: 2026-04-01", "url": "https://github.com/a/b/issues/11"},
                    "run_url": "https://github.com/a/b/actions/runs/1",
                }
            ],
            "repo_action_summary": {
                "CryptoLeaderRotation": {
                    "actions": [
                        {
                            "risk_level": "low",
                            "title": "Add challenger breadth check",
                            "summary": "Improve evidence coverage.",
                            "source_repo": "QuantStrategyLab/CryptoLeaderRotation",
                            "source_issue_number": 11,
                            "auto_pr_safe": True,
                            "experiment_only": True,
                        }
                    ]
                }
            },
            "operator_focus": ["QuantStrategyLab/CryptoLeaderRotation: Need more evidence."],
        }

        markdown = render_summary_markdown(plan)

        self.assertIn("# Monthly Optimization Planner", markdown)
        self.assertIn("QuantStrategyLab/CryptoLeaderRotation", markdown)
        self.assertIn("Add challenger breadth check", markdown)
        self.assertIn("Operator Focus", markdown)


if __name__ == "__main__":
    unittest.main()
