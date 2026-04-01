from __future__ import annotations

import unittest

from scripts.render_monthly_ai_review import build_full_review_markdown, render_secondary_review_markdown


class RenderMonthlyAiReviewTests(unittest.TestCase):
    def test_render_secondary_review_markdown_includes_actions_and_flags(self) -> None:
        payload = {
            "provider_display_name": "GPT Secondary Review",
            "verdict": "partial_agree",
            "risk_level": "medium",
            "production_recommendation": "research_only",
            "summary": "Evidence is directionally fine but still incomplete.",
            "key_findings": ["Shadow coverage is still thin."],
            "recommended_actions": [
                {
                    "title": "Add another challenger track",
                    "owner_repo": "CryptoLeaderRotation",
                    "risk_level": "low",
                    "auto_pr_safe": True,
                    "experiment_only": True,
                    "summary": "Improve monthly evidence before changing production.",
                }
            ],
            "follow_up_checks": ["Compare challenger turnover before next promotion."],
        }

        markdown = render_secondary_review_markdown(payload)

        self.assertIn("## Secondary Review (GPT Secondary Review)", markdown)
        self.assertIn("`partial_agree`", markdown)
        self.assertIn("auto-pr-safe", markdown)
        self.assertIn("experiment-only", markdown)
        self.assertIn("Compare challenger turnover", markdown)

    def test_build_full_review_markdown_includes_primary_and_secondary_sections(self) -> None:
        markdown = build_full_review_markdown(
            "## English\nPrimary review",
            primary_title="Claude Primary Review",
            secondary_review_payload={
                "provider_display_name": "GPT Secondary Review",
                "verdict": "agree",
                "risk_level": "low",
                "production_recommendation": "keep_production_as_is",
                "summary": "Looks consistent.",
                "key_findings": ["No blocking issue found."],
                "recommended_actions": [],
                "follow_up_checks": [],
            },
        )

        self.assertIn("## Claude Primary Review", markdown)
        self.assertIn("## Secondary Review (GPT Secondary Review)", markdown)
        self.assertIn("## English", markdown)


if __name__ == "__main__":
    unittest.main()
