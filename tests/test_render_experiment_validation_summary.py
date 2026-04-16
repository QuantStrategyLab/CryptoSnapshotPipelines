from __future__ import annotations

import unittest

from scripts.render_experiment_validation_summary import build_summary_markdown


class RenderExperimentValidationSummaryTests(unittest.TestCase):
    def test_build_summary_includes_shadow_track_details(self) -> None:
        payload = {
            "issue_number": 22,
            "issue_title": "Monthly Optimization Tasks · CryptoSnapshotPipelines",
            "should_run": True,
            "experiment_task_count": 1,
            "experiment_actions": [
                {
                    "risk_level": "low",
                    "title": "Run monthly shadow build and archive challenger summaries",
                    "flags": ["auto-pr-safe", "experiment-only"],
                    "summary": "Generate official_baseline and challenger_topk_60 coverage each month.",
                }
            ],
            "skip_reason": "",
        }
        shadow_summary = {
            "as_of_date": "2026-04-01",
            "official_baseline": {"version": "2026-04-01-core_major", "mode": "core_major", "pool_size": 5},
            "shadow_candidate_tracks": {
                "tracks": [
                    {"track_id": "challenger_topk_60", "profile_name": "challenger_topk_60", "pool_size": 5}
                ]
            },
        }

        summary = build_summary_markdown(payload, shadow_summary)

        self.assertIn("Monthly Experiment Validation", summary)
        self.assertIn("Official baseline version", summary)
        self.assertIn("challenger_topk_60", summary)


if __name__ == "__main__":
    unittest.main()
