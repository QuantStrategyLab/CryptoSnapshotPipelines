from __future__ import annotations

import argparse
import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_API_URL = "https://api.github.com"
ARTIFACT_PREFIX = "ai-monthly-review-"


def github_request(url: str, token: str, api_url: str = DEFAULT_API_URL) -> Any:
    request = urllib.request.Request(
        url if url.startswith("http") else f"{api_url.rstrip('/')}/{url.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "monthly-optimization-planner",
        },
    )
    with urllib.request.urlopen(request) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read()
        if "application/json" in content_type:
            charset = response.headers.get_content_charset("utf-8")
            return json.loads(body.decode(charset))
        return body


def select_ai_review_artifact(artifacts_payload: dict[str, Any]) -> dict[str, Any]:
    artifacts = artifacts_payload.get("artifacts") or []
    candidates = [artifact for artifact in artifacts if str(artifact.get("name", "")).startswith(ARTIFACT_PREFIX)]
    if not candidates:
        raise ValueError("No ai-monthly-review artifact found for the workflow run")
    candidates.sort(key=lambda artifact: int(artifact.get("id", 0)), reverse=True)
    return candidates[0]


def download_and_extract_artifact(*, repo: str, run_id: int, token: str, output_dir: Path) -> Path:
    artifacts_payload = github_request(f"repos/{repo}/actions/runs/{run_id}/artifacts", token)
    artifact = select_ai_review_artifact(artifacts_payload)
    archive = github_request(artifact["archive_download_url"], token)
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as handle:
        handle.extractall(output_dir)
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and extract the ai-monthly-review artifact from a workflow run.",
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"{args.token_env} is required")
    download_and_extract_artifact(repo=args.repo, run_id=args.run_id, token=token, output_dir=args.output_dir)
    print(f"artifact_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
