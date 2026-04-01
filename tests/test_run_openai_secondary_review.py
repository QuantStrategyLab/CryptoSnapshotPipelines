from __future__ import annotations

import json
import unittest

from scripts.run_openai_secondary_review import (
    build_request_payload,
    build_system_prompt,
    extract_completion_content,
)


class RunOpenAiSecondaryReviewTests(unittest.TestCase):
    def test_build_system_prompt_for_upstream_selector_mentions_shadow_and_binanceplatform(self) -> None:
        prompt = build_system_prompt("upstream_selector")

        self.assertIn("CryptoLeaderRotation", prompt)
        self.assertIn("shadow/challenger", prompt)
        self.assertIn("BinancePlatform", prompt)

    def test_build_request_payload_uses_structured_json_schema(self) -> None:
        payload = build_request_payload(
            model="gpt-5.4-mini",
            review_kind="upstream_selector",
            issue_title="Monthly Review",
            issue_body="body",
            primary_review_text="primary",
        )

        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertIn("messages", payload)

    def test_extract_completion_content_reads_first_choice_message(self) -> None:
        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"summary": "ok"}),
                    }
                }
            ]
        }

        self.assertEqual(extract_completion_content(response_payload), '{"summary": "ok"}')


if __name__ == "__main__":
    unittest.main()
