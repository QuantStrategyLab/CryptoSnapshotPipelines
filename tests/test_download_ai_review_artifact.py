from __future__ import annotations

import unittest

from scripts.download_ai_review_artifact import select_ai_review_artifact


class DownloadAiReviewArtifactTests(unittest.TestCase):
    def test_select_ai_review_artifact_picks_latest_matching_artifact(self) -> None:
        artifact = select_ai_review_artifact(
            {
                "artifacts": [
                    {"id": 10, "name": "other-artifact"},
                    {"id": 20, "name": "ai-monthly-review-9"},
                    {"id": 30, "name": "ai-monthly-review-11"},
                ]
            }
        )

        self.assertEqual(artifact["id"], 30)
        self.assertEqual(artifact["name"], "ai-monthly-review-11")


if __name__ == "__main__":
    unittest.main()
