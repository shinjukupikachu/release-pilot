from __future__ import annotations
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

TEST_DATA = Path(__file__).parent / "test_data"

mcp = FastMCP("release-pilot-mock")


@mcp.tool()
def get_jira_issue(key: str) -> dict:
    """Get a Jira issue by key (e.g. NYANKO-456).
    Returns issue summary, status, type, and priority."""
    data = json.loads((TEST_DATA / "jira_issues.json").read_text())
    return data.get(key, {"error": "not_found", "key": key})


@mcp.tool()
def search_jira_issues(fix_version: str) -> list:
    """Search Jira issues by fix version (e.g. 'v2.3.0').
    Returns all issues linked to the release."""
    data = json.loads((TEST_DATA / "jira_issues.json").read_text())
    return list(data.values())


@mcp.tool()
def get_github_pr(commit_sha: str) -> dict:
    """Get the GitHub Pull Request associated with a commit SHA.
    Returns PR number, title, URL, and author."""
    data = json.loads((TEST_DATA / "github_prs.json").read_text())
    return data.get(commit_sha, {"error": "not_found", "commit_sha": commit_sha})


@mcp.tool()
def get_check_runs(commit_sha: str) -> dict:
    """Get CI check-run results for a commit SHA.
    Returns total, passed, failed counts and names of failing checks."""
    data = json.loads((TEST_DATA / "github_check_runs.json").read_text())
    return data.get(
        commit_sha, {"total": 0, "passed": 0, "failed": 0, "failed_names": []}
    )


if __name__ == "__main__":
    mcp.run()
