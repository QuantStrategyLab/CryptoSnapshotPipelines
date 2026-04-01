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


COMMENT_MARKER_PREFIX = "<!-- monthly-optimization-task:"
DEFAULT_API_URL = "https://api.github.com"
LABEL_NAME = "monthly-optimization-task"
LABEL_COLOR = "5319E7"
LABEL_DESCRIPTION = "Automated repo-scoped monthly optimization tasks"
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def build_marker(plan: dict[str, Any], owner_repo: str) -> str:
    source_parts = [
        f"{review['source_repo']}#{review['source_issue']['number']}"
        for review in plan.get("source_reviews", [])
    ]
    return f"{COMMENT_MARKER_PREFIX}{owner_repo}:{'|'.join(source_parts)} -->"


def build_marker_from_body(body: str) -> str:
    for line in body.splitlines():
        if line.startswith(COMMENT_MARKER_PREFIX):
            return line.strip()
    return ""


def build_issue_title(plan: dict[str, Any], owner_repo: str) -> str:
    labels = [review["source_issue"]["title"].split(": ", 1)[-1] for review in plan.get("source_reviews", [])]
    return f"Monthly Optimization Tasks · {owner_repo}: {' / '.join(labels)}"


def _repo_actions(plan: dict[str, Any], owner_repo: str) -> list[dict[str, Any]]:
    repo_summary = plan.get("repo_action_summary", {}).get(owner_repo, {})
    return list(repo_summary.get("actions", []))


def build_issue_body(plan: dict[str, Any], owner_repo: str, planner_issue_url: str | None = None) -> str:
    actions = _repo_actions(plan, owner_repo)
    repo_summary = plan.get("repo_action_summary", {}).get(owner_repo, {})
    safe_auto_pr_count = sum(1 for action in actions if action.get("auto_pr_safe"))
    experiment_count = sum(1 for action in actions if action.get("experiment_only"))
    lines = [
        build_marker(plan, owner_repo),
        f"# Monthly Optimization Tasks · {owner_repo}",
        "",
        f"- Actions in this repo: `{len(actions)}`",
        f"- Highest repo risk: `{repo_summary.get('highest_risk_level', 'low')}`",
        f"- Safe auto-PR candidates here: `{safe_auto_pr_count}`",
        f"- Experiment-only tasks here: `{experiment_count}`",
    ]
    if planner_issue_url:
        lines.append(f"- Planner issue: {planner_issue_url}")

    lines.extend(["", "## Actions"])
    for action in actions:
        flags: list[str] = []
        if action.get("auto_pr_safe"):
            flags.append("auto-pr-safe")
        if action.get("experiment_only"):
            flags.append("experiment-only")
        flag_suffix = f" [{', '.join(flags)}]" if flags else ""
        lines.extend(
            [
                f"- [ ] `{action['risk_level']}` {action['title']}{flag_suffix}",
                f"  - Summary: {action['summary']}",
                f"  - Source: [{action['source_repo']} #{action['source_issue_number']}]({action['source_issue_url']})",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def build_closed_issue_body(plan: dict[str, Any], owner_repo: str, planner_issue_url: str | None = None) -> str:
    lines = [
        build_marker(plan, owner_repo),
        f"# Monthly Optimization Tasks · {owner_repo}",
        "",
        "No repo-scoped tasks remain in the current monthly optimization plan.",
        "This issue is being closed to avoid leaving stale automation targets behind.",
    ]
    if planner_issue_url:
        lines.extend(["", f"- Planner issue: {planner_issue_url}"])
    return "\n".join(lines).strip() + "\n"


def github_request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "monthly-optimization-fanout",
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


def upsert_issue(*, api_url: str, repo: str, token: str, title: str, body: str) -> tuple[str, int, str]:
    marker = build_marker_from_body(body)
    existing = find_existing_issue(api_url=api_url, repo=repo, token=token, marker=marker)
    payload = {"title": title, "body": body, "labels": [LABEL_NAME]}
    if existing:
        github_request("PATCH", f"{api_url}/repos/{repo}/issues/{existing['number']}", token, payload)
        return "updated", int(existing["number"]), str(existing["html_url"])
    created = github_request("POST", f"{api_url}/repos/{repo}/issues", token, payload)
    return "created", int(created["number"]), str(created["html_url"])


def find_existing_issue(*, api_url: str, repo: str, token: str, marker: str) -> dict[str, Any] | None:
    issues = github_request(
        "GET",
        f"{api_url}/repos/{repo}/issues?state=open&labels={urllib.parse.quote(LABEL_NAME)}&per_page=100",
        token,
    )
    return next((issue for issue in issues if build_marker_from_body(issue.get("body", "")) == marker), None)


def close_existing_issue(
    *,
    api_url: str,
    repo: str,
    token: str,
    title: str,
    body: str,
) -> tuple[bool, int | None, str | None]:
    marker = build_marker_from_body(body)
    existing = find_existing_issue(api_url=api_url, repo=repo, token=token, marker=marker)
    if not existing:
        return False, None, None
    github_request(
        "PATCH",
        f"{api_url}/repos/{repo}/issues/{existing['number']}",
        token,
        {"title": title, "body": body, "state": "closed", "labels": [LABEL_NAME]},
    )
    return True, int(existing["number"]), str(existing["html_url"])


def build_result(
    *,
    owner_repo: str,
    target_repo: str,
    plan: dict[str, Any],
    status: str,
    issue_number: int | None = None,
    issue_url: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    repo_summary = plan.get("repo_action_summary", {}).get(owner_repo, {})
    return {
        "owner_repo": owner_repo,
        "target_repo": target_repo,
        "status": status,
        "actions_count": int(repo_summary.get("count", 0)),
        "highest_risk_level": repo_summary.get("highest_risk_level", "low"),
        "issue_number": issue_number,
        "issue_url": issue_url,
        "reason": reason,
    }


def write_result(output_file: Path, result: dict[str, Any]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update repo-scoped monthly optimization task issues.",
    )
    parser.add_argument("--plan-file", required=True, type=Path)
    parser.add_argument("--owner-repo", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output-file", required=True, type=Path)
    parser.add_argument("--planner-issue-url")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--allow-permission-skip", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
    actions = _repo_actions(plan, args.owner_repo)
    if not actions:
        title = build_issue_title(plan, args.owner_repo)
        body = build_closed_issue_body(plan, args.owner_repo, planner_issue_url=args.planner_issue_url)
        try:
            closed, issue_number, issue_url = close_existing_issue(
                api_url=args.api_url.rstrip("/"),
                repo=args.repo,
                token=token,
                title=title,
                body=body,
            )
            result = build_result(
                owner_repo=args.owner_repo,
                target_repo=args.repo,
                plan=plan,
                status="closed_no_actions" if closed else "skipped_no_actions",
                issue_number=issue_number,
                issue_url=issue_url,
                reason=None if closed else "No recommended actions for this repo in the current optimization plan.",
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if args.allow_permission_skip and exc.code in {403, 404}:
                result = build_result(
                    owner_repo=args.owner_repo,
                    target_repo=args.repo,
                    plan=plan,
                    status="skipped_permission",
                    reason=f"{exc.code}: {detail or 'permission denied or repo not accessible'}",
                )
                write_result(args.output_file, result)
                print(json.dumps(result, ensure_ascii=False))
                return 0
            print(f"GitHub API request failed: {exc.code} {detail}", file=sys.stderr)
            return 1
        write_result(args.output_file, result)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    title = build_issue_title(plan, args.owner_repo)
    body = build_issue_body(plan, args.owner_repo, planner_issue_url=args.planner_issue_url)

    try:
        ensure_label(args.api_url.rstrip("/"), args.repo, token)
        status, issue_number, issue_url = upsert_issue(
            api_url=args.api_url.rstrip("/"),
            repo=args.repo,
            token=token,
            title=title,
            body=body,
        )
        result = build_result(
            owner_repo=args.owner_repo,
            target_repo=args.repo,
            plan=plan,
            status=status,
            issue_number=issue_number,
            issue_url=issue_url,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if args.allow_permission_skip and exc.code in {403, 404}:
            result = build_result(
                owner_repo=args.owner_repo,
                target_repo=args.repo,
                plan=plan,
                status="skipped_permission",
                reason=f"{exc.code}: {detail or 'permission denied or repo not accessible'}",
            )
            write_result(args.output_file, result)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        print(f"GitHub API request failed: {exc.code} {detail}", file=sys.stderr)
        return 1

    write_result(args.output_file, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
