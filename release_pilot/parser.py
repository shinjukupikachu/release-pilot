from __future__ import annotations

import re

from release_pilot.models import CommitInfo, ParsedCommit

# Conventional commit subject: type(scope)!: description
_SUBJECT_RE = re.compile(r"^(\w+)(\([\w/.-]+\))?(!)?:\s*(.+)")
# Jira key pattern
_JIRA_RE = re.compile(r"[A-Z]+-\d+")
_BREAKING_RE = re.compile(r"^BREAKING CHANGE:\s*(.+)", re.MULTILINE)


def parse_subject(subject: str) -> tuple[str, str | None, bool, str]:
    """Returns (commit_type, scope, is_breaking, clean_subject)."""
    m = _SUBJECT_RE.match(subject)
    if not m:
        return "chore", None, False, subject
    commit_type = m.group(1).lower()
    scope = m.group(2)[1:-1] if m.group(2) else None  # strip parens
    is_breaking = m.group(3) == "!"
    clean_subject = m.group(4)
    return commit_type, scope, is_breaking, clean_subject


def parse_body(body: str) -> tuple[str | None, list[str]]:
    """Returns (breaking_note, jira_keys) from commit body."""
    breaking_note: str | None = None
    m = _BREAKING_RE.search(body)
    if m:
        breaking_note = m.group(1).strip()
    jira_keys = list(dict.fromkeys(_JIRA_RE.findall(body)))  # deduplicated, order-preserving
    return breaking_note, jira_keys


def parse_commit(commit: CommitInfo) -> ParsedCommit:
    commit_type, scope, is_breaking_subject, clean_subject = parse_subject(commit.subject)
    breaking_note, jira_keys = parse_body(commit.body)
    is_breaking = is_breaking_subject or breaking_note is not None
    # Also extract Jira keys from subject
    subject_keys = _JIRA_RE.findall(commit.subject)
    all_keys = list(dict.fromkeys(subject_keys + jira_keys))
    return ParsedCommit(
        hash=commit.hash,
        short_hash=commit.short_hash,
        author=commit.author,
        date=commit.date,
        subject=commit.subject,
        body=commit.body,
        commit_type=commit_type,
        scope=scope,
        is_breaking=is_breaking,
        breaking_note=breaking_note,
        clean_subject=clean_subject,
        jira_keys=all_keys,
    )


def parse_commits(commits: list[CommitInfo]) -> list[ParsedCommit]:
    return [parse_commit(c) for c in commits]
