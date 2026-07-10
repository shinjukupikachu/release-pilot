"""Release readiness check: commits → Jira → author/manager grouping."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from release_pilot import config
from release_pilot import org as orgchart

_JIRA_KEY_RE = re.compile(r"NYANKO-\d+")
_TEST_DATA = Path(__file__).parent.parent / "test_data"


@dataclass
class CommitInfo:
    short_hash: str
    subject: str
    author: str
    jira_keys: list[str]


@dataclass
class JiraInfo:
    key: str
    summary: str
    status: str
    issue_type: str
    priority: str


@dataclass
class AuthorGroup:
    author: str
    title: str
    manager_name: str
    manager_slack: str
    commits: list[CommitInfo] = field(default_factory=list)
    jira_tickets: list[JiraInfo] = field(default_factory=list)

    @property
    def open_tickets(self) -> list[JiraInfo]:
        return [
            t for t in self.jira_tickets if t.status.lower() not in ("done", "closed", "resolved")
        ]

    @property
    def closed_tickets(self) -> list[JiraInfo]:
        return [t for t in self.jira_tickets if t.status.lower() in ("done", "closed", "resolved")]


@dataclass
class ReadinessCheckResult:
    version: str | None
    from_ref: str | None
    author_groups: list[AuthorGroup]
    all_jira: list[JiraInfo]
    sign_off_managers: list[str]

    @property
    def total_commits(self) -> int:
        return sum(len(g.commits) for g in self.author_groups)

    @property
    def open_count(self) -> int:
        return sum(len(g.open_tickets) for g in self.author_groups)

    @property
    def closed_count(self) -> int:
        return sum(len(g.closed_tickets) for g in self.author_groups)

    @property
    def is_ready(self) -> bool:
        return self.open_count == 0


def _load_jira_data() -> dict[str, dict]:
    path = _TEST_DATA / "jira_issues.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _load_commits_from_test_data() -> list[dict]:
    path = _TEST_DATA / "commits.json"
    if path.exists():
        return json.loads(path.read_text())
    return []


def _load_commits_from_db(version: str, db_path: str = config.DB_PATH) -> list[dict] | None:
    """Return commit dicts from DB traceability for a known version, or None if not found."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            release = conn.execute(
                "SELECT id, from_ref FROM releases WHERE version = ?", (version,)
            ).fetchone()
            if not release:
                return None, None
            rows = conn.execute(
                "SELECT short_hash, description, jira_keys FROM traceability_rows WHERE release_id = ?",
                (release["id"],),
            ).fetchall()
        commits = []
        for r in rows:
            commits.append(
                {
                    "short_hash": r["short_hash"],
                    "subject": r["description"],
                    "author": "Unknown",
                    "jira_keys_parsed": json.loads(r["jira_keys"] or "[]"),
                }
            )
        return commits, release["from_ref"]
    except Exception:
        return None, None


def run_check(version: str | None = None) -> ReadinessCheckResult:
    jira_db = _load_jira_data()
    from_ref = None

    raw_commits: list[dict] = []
    pre_parsed_keys: dict[str, list[str]] = {}  # short_hash → keys

    if version:
        db_result, from_ref = _load_commits_from_db(version)
        if db_result:
            for c in db_result:
                raw_commits.append(
                    {
                        "short_hash": c["short_hash"],
                        "subject": c["subject"],
                        "author": c.get("author", "Unknown"),
                    }
                )
                pre_parsed_keys[c["short_hash"]] = c.get("jira_keys_parsed", [])

    if not raw_commits:
        raw_commits = _load_commits_from_test_data()

    # Parse commits into CommitInfo objects
    commit_infos: list[CommitInfo] = []
    for c in raw_commits:
        full_text = f"{c.get('subject', '')} {c.get('body', '')}"
        keys = pre_parsed_keys.get(c.get("short_hash", "")) or _JIRA_KEY_RE.findall(full_text)
        commit_infos.append(
            CommitInfo(
                short_hash=c.get("short_hash", ""),
                subject=c.get("subject", ""),
                author=c.get("author", "Unknown"),
                jira_keys=list(dict.fromkeys(keys)),  # dedupe, preserve order
            )
        )

    # Collect all unique Jira keys
    all_keys: list[str] = []
    seen_keys: set[str] = set()
    for ci in commit_infos:
        for k in ci.jira_keys:
            if k not in seen_keys:
                all_keys.append(k)
                seen_keys.add(k)

    # Build JiraInfo objects
    def _jira_info(key: str) -> JiraInfo:
        raw = jira_db.get(key, {})
        fields = raw.get("fields", {})
        return JiraInfo(
            key=key,
            summary=fields.get("summary", "(no summary)"),
            status=fields.get("status", {}).get("name", "Unknown"),
            issue_type=fields.get("issuetype", {}).get("name", ""),
            priority=fields.get("priority", {}).get("name", ""),
        )

    jira_by_key = {k: _jira_info(k) for k in all_keys}

    # Group by author
    author_groups: dict[str, AuthorGroup] = {}
    for ci in commit_infos:
        author = ci.author
        if author not in author_groups:
            person = orgchart.lookup(author)
            manager = orgchart.manager_of(author)
            author_groups[author] = AuthorGroup(
                author=author,
                title=person.title if person else "Engineer",
                manager_name=manager.name if manager else "Unknown",
                manager_slack=manager.slack_handle if manager else "",
            )
        grp = author_groups[author]
        grp.commits.append(ci)
        for k in ci.jira_keys:
            if k in jira_by_key and jira_by_key[k] not in grp.jira_tickets:
                grp.jira_tickets.append(jira_by_key[k])

    # Collect unique managers for sign-off
    managers_seen: set[str] = set()
    sign_off_managers: list[str] = []
    for grp in author_groups.values():
        if grp.manager_name and grp.manager_name not in managers_seen:
            managers_seen.add(grp.manager_name)
            sign_off_managers.append(grp.manager_name)

    return ReadinessCheckResult(
        version=version,
        from_ref=from_ref,
        author_groups=list(author_groups.values()),
        all_jira=list(jira_by_key.values()),
        sign_off_managers=sign_off_managers,
    )
