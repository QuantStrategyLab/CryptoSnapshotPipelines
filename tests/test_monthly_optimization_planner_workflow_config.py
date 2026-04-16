from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "monthly_optimization_planner.yml"


class MonthlyOptimizationPlannerWorkflowConfigTests(unittest.TestCase):
    def test_planner_workflow_downloads_artifacts_posts_issue_and_fans_out_tasks(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("upstream_run_id:", workflow)
        self.assertIn("downstream_run_id:", workflow)
        self.assertIn("downstream_repo:", workflow)
        self.assertIn("actions: write", workflow)
        self.assertIn("CROSS_REPO_GITHUB_TOKEN", workflow)
        self.assertIn("CROSS_REPO_GITHUB_APP_PRIVATE_KEY", workflow)
        self.assertIn("CROSS_REPO_GITHUB_APP_ID", workflow)
        self.assertIn("Detect GitHub App credentials", workflow)
        self.assertIn("has_app_credentials", workflow)
        self.assertIn("actions/create-github-app-token@v3", workflow)
        self.assertIn("Resolve cross-repo access token", workflow)
        self.assertIn("source=github_app", workflow)
        self.assertIn("source=personal_access_token", workflow)
        self.assertIn("gh run download", workflow)
        self.assertIn("Resolve downloaded artifact paths", workflow)
        self.assertIn("Prepare upstream review payload", workflow)
        self.assertIn("Prepare downstream review payload", workflow)
        self.assertIn("build_ai_review_payload.py", workflow)
        self.assertIn("build_monthly_optimization_plan.py", workflow)
        self.assertIn("post_monthly_optimization_issue.py", workflow)
        self.assertIn("fanout_monthly_optimization_tasks.py", workflow)
        self.assertIn("Fan out CryptoSnapshotPipelines task issue", workflow)
        self.assertIn("Fan out CryptoStrategies task issue", workflow)
        self.assertIn("Fan out BinancePlatform task issue", workflow)
        self.assertIn("Resolve upstream experiment validation target", workflow)
        self.assertIn("Dispatch CryptoSnapshotPipelines experiment validation", workflow)
        self.assertIn("Resolve downstream experiment validation target", workflow)
        self.assertIn("Best-effort label BinancePlatform issue for experiment validation", workflow)
        self.assertIn("experiment-validation", workflow)
        self.assertIn("Dispatch BinancePlatform experiment validation", workflow)
        self.assertIn("gh workflow run experiment_validation.yml", workflow)
        self.assertIn("--allow-permission-skip", workflow)
        self.assertIn("Append fanout summary", workflow)
        self.assertIn("upstream_review_payload.json", workflow)
        self.assertIn("downstream_review_payload.json", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("monthly-optimization-plan-", workflow)


if __name__ == "__main__":
    unittest.main()
