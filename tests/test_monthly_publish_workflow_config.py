from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "monthly_publish.yml"
AI_REVIEW_WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ai_review.yml"


class MonthlyPublishWorkflowConfigTests(unittest.TestCase):
    def test_publish_targets_use_vars_only(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("actions: write", workflow)
        self.assertIn("GCP_PROJECT_ID: ${{ vars.GCP_PROJECT_ID }}", workflow)
        self.assertIn("GCS_BUCKET: ${{ vars.GCS_BUCKET }}", workflow)
        self.assertIn("credentials_json: ${{ secrets.GCP_SERVICE_ACCOUNT_KEY }}", workflow)
        self.assertIn("issues: write", workflow)
        self.assertNotIn("secrets.GCP_PROJECT_ID", workflow)
        self.assertNotIn("secrets.GCS_BUCKET", workflow)

    def test_monthly_review_issue_creation_does_not_require_gh_cli(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertNotIn("gh label create", workflow)
        self.assertNotIn("gh issue create", workflow)
        self.assertNotIn("gh workflow run", workflow)
        self.assertIn("run_monthly_shadow_build.py", workflow)
        self.assertIn("--skip-publish-dry-run", workflow)
        self.assertIn("--shadow-universe-mode", workflow)
        self.assertIn("https://api.github.com/repos/{repository}", workflow)
        self.assertIn('GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}', workflow)
        self.assertIn("issue_number=", workflow)
        self.assertIn("/actions/workflows/ai_review.yml/dispatches", workflow)

    def test_ai_review_workflow_supports_dispatch_and_comment_posting(self) -> None:
        workflow = AI_REVIEW_WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("issue_number:", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("Load review issue context", workflow)
        self.assertIn("api.github.com/repos/{repo}/issues/{issue_number}", workflow)
        self.assertIn("github_token: ${{ secrets.GITHUB_TOKEN }}", workflow)
        self.assertIn("This is a strategy-optimization review, not only a release QA check.", workflow)
        self.assertIn("If shadow or challenger tracks are missing, say evidence is incomplete", workflow)
        self.assertIn("Strategy Optimization Directions", workflow)
        self.assertIn("post_monthly_ai_review_comment.py", workflow)
        self.assertIn("steps.claude_review.outputs.execution_file", workflow)
        self.assertNotIn("model:", workflow)
        self.assertNotIn("allowed_tools:", workflow)
        self.assertNotIn("custom_instructions:", workflow)


if __name__ == "__main__":
    unittest.main()
