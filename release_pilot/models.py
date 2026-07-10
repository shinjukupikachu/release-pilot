from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CommitInfo:
    hash: str  # full 40-char SHA
    short_hash: str  # 7-char short SHA
    author: str
    date: str  # ISO 8601
    subject: str
    body: str  # may be empty string


@dataclass
class JiraTicket:
    key: str  # e.g. NYANKO-456
    summary: str
    status: str  # e.g. "Done"
    issue_type: str  # e.g. "Bug", "Story", "Task"
    priority: str | None = None


@dataclass
class CIStatus:
    total: int
    passed: int
    failed: int
    failed_names: list[str] = field(default_factory=list)


@dataclass
class ParsedCommit:
    # inherited CommitInfo fields (copy them, don't subclass)
    hash: str
    short_hash: str
    author: str
    date: str
    subject: str
    body: str
    # parsed fields
    commit_type: str  # feat, fix, chore, perf, refactor, ci, build, docs
    scope: str | None  # e.g. "picking", "api"
    is_breaking: bool  # True if ! suffix or BREAKING CHANGE in body
    breaking_note: str | None  # text after "BREAKING CHANGE: " in body
    clean_subject: str  # subject without type(scope)!: prefix
    jira_keys: list[str] = field(default_factory=list)  # e.g. ["NYANKO-456"]
    audience: str | None = None  # "internal" | "customer" | "marketing" — set by classifier agent
    # enrichment fields (set after MCP phase)
    jira_tickets: list[JiraTicket] = field(default_factory=list)
    pr_number: int | None = None
    pr_url: str | None = None
    pr_title: str | None = None
    ci_status: CIStatus | None = None


@dataclass
class TraceabilityRow:
    short_hash: str
    description: str
    commit_type: str
    is_breaking: bool
    jira_tickets: list[JiraTicket] = field(default_factory=list)
    pr_number: int | None = None
    pr_url: str | None = None
    ci_status: CIStatus | None = None


@dataclass
class ChangeSet:
    version: str  # e.g. "v2.3.0"
    from_ref: str  # e.g. "v2.2.0"
    commits: list[ParsedCommit] = field(default_factory=list)
    breaking: list[ParsedCommit] = field(default_factory=list)
    suggested_bump: str = "none"  # "major" | "minor" | "patch" | "none"


@dataclass
class ReadinessReport:
    score: int  # 0–100
    recommendation: str  # "READY" | "HOLD" | "BLOCKED"
    rationale: str
    risk_factors: list[str] = field(default_factory=list)
    rollback_plan: str = ""


@dataclass
class ReleaseResult:
    version: str
    suggested_bump: str
    readiness: ReadinessReport
    internal_announcement: str
    customer_notes: str
    traceability: list[TraceabilityRow] = field(default_factory=list)
    marketing_notes: str | None = None  # None if no marketing-tier commits


@dataclass
class ReleaseSummary:
    version: str
    created_at: str
    recommendation: str
    readiness_score: int
    suggested_bump: str
