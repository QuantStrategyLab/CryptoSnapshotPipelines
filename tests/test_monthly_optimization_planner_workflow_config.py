from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "monthly_optimization_planner.yml"


class MonthlyOptimizationPlannerWorkflowConfigTests(unittest.TestCase):
    def test_planner_workflow_downloads_artifacts_and_posts_issue(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("upstream_run_id:", workflow)
        self.assertIn("downstream_run_id:", workflow)
        self.assertIn("downstream_repo:", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("CROSS_REPO_GITHUB_TOKEN", workflow)
        self.assertIn("gh run download", workflow)
        self.assertIn("Resolve downloaded artifact paths", workflow)
        self.assertIn("Prepare upstream review payload", workflow)
        self.assertIn("Prepare downstream review payload", workflow)
        self.assertIn("build_ai_review_payload.py", workflow)
        self.assertIn("build_monthly_optimization_plan.py", workflow)
        self.assertIn("post_monthly_optimization_issue.py", workflow)
        self.assertIn("upstream_review_payload.json", workflow)
        self.assertIn("downstream_review_payload.json", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("monthly-optimization-plan-", workflow)


if __name__ == "__main__":
    unittest.main()
