from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


COMMENT_MARKER_PREFIX = "<!-- monthly-optimization-plan:"
DEFAULT_API_URL = "https://api.github.com"
LABEL_NAME = "monthly-optimization"
LABEL_COLOR = "1D76DB"
LABEL_DESCRIPTION = "Automated monthly optimization planning"


def build_marker(plan: dict[str, Any]) -> str:
    source_parts = [
        f"{review['source_repo']}#{review['source_issue']['number']}"
        for review in plan.get("source_reviews", [])
    ]
    return f"{COMMENT_MARKER_PREFIX}{'|'.join(source_parts)} -->"


def build_issue_title(plan: dict[str, Any]) -> str:
    labels = [review["source_issue"]["title"].split(": ", 1)[-1] for review in plan.get("source_reviews", [])]
    return f"Monthly Optimization Plan: {' / '.join(labels)}"


def build_issue_body(plan: dict[str, Any], summary_markdown: str) -> str:
    marker = build_marker(plan)
    return f"{marker}\n{summary_markdown.strip()}"


def github_request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "monthly-optimization-planner",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        charset = response.headers.get_content_charset("utf-8")
        raw = response.read().decode(charset)
        return json.loads(raw) if raw else None


def ensure_label(api_url: str, repo: str, token: str) -> None:
    label_path = urllib.parse.quote(LABEL_NAME, safe="")
    label_url = f"{api_url}/repos/{repo}/labels/{label_path}"
    try:
        github_request("GET", label_url, token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        github_request(
            "POST",
            f"{api_url}/repos/{repo}/labels",
            token,
            {
                "name": LABEL_NAME,
                "color": LABEL_COLOR,
                "description": LABEL_DESCRIPTION,
            },
        )


def upsert_issue(*, api_url: str, repo: str, token: str, title: str, body: str) -> int:
    issues = github_request(
        "GET",
        f"{api_url}/repos/{repo}/issues?state=open&labels={urllib.parse.quote(LABEL_NAME)}&per_page=100",
        token,
    )
    existing = next((issue for issue in issues if build_marker_from_body(issue.get("body", "")) == build_marker_from_body(body)), None)
    payload = {"title": title, "body": body, "labels": [LABEL_NAME]}
    if existing:
        github_request("PATCH", f"{api_url}/repos/{repo}/issues/{existing['number']}", token, payload)
        print(f"Updated optimization issue #{existing['number']}")
        return int(existing["number"])
    created = github_request("POST", f"{api_url}/repos/{repo}/issues", token, payload)
    print(f"Created optimization issue #{created['number']}")
    return int(created["number"])


def build_marker_from_body(body: str) -> str:
    for line in body.splitlines():
        if line.startswith(COMMENT_MARKER_PREFIX):
            return line.strip()
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update the monthly optimization issue from the planner outputs.",
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--plan-file", required=True, type=Path)
    parser.add_argument("--summary-file", required=True, type=Path)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
    summary_markdown = args.summary_file.read_text(encoding="utf-8")
    title = build_issue_title(plan)
    body = build_issue_body(plan, summary_markdown)

    try:
        ensure_label(args.api_url.rstrip("/"), args.repo, token)
        issue_number = upsert_issue(
            api_url=args.api_url.rstrip("/"),
            repo=args.repo,
            token=token,
            title=title,
            body=body,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"GitHub API request failed: {exc.code} {detail}", file=sys.stderr)
        return 1

    print(f"issue_number={issue_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
