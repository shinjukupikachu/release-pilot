from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from release_pilot import config
from release_pilot.models import (
    CIStatus,
    JiraTicket,
    ReadinessReport,
    ReleaseResult,
    ReleaseSummary,
    TraceabilityRow,
)

_CREATE_RELEASES = """
CREATE TABLE IF NOT EXISTS releases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT NOT NULL UNIQUE,
    from_ref        TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    readiness_score INTEGER NOT NULL,
    recommendation  TEXT NOT NULL,
    suggested_bump  TEXT NOT NULL,
    internal_announcement TEXT NOT NULL,
    customer_notes  TEXT NOT NULL,
    marketing_notes TEXT
)
"""

_CREATE_TRACEABILITY = """
CREATE TABLE IF NOT EXISTS traceability_rows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    release_id      INTEGER NOT NULL REFERENCES releases(id),
    short_hash      TEXT NOT NULL,
    description     TEXT NOT NULL,
    commit_type     TEXT NOT NULL,
    is_breaking     INTEGER NOT NULL DEFAULT 0,
    jira_keys       TEXT NOT NULL,
    jira_statuses   TEXT NOT NULL,
    pr_number       INTEGER,
    pr_url          TEXT,
    ci_total        INTEGER,
    ci_passed       INTEGER,
    ci_failed       INTEGER,
    ci_failed_names TEXT
)
"""


def init_db(db_path: str = config.DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(_CREATE_RELEASES)
        conn.execute(_CREATE_TRACEABILITY)
        conn.commit()


def save_release(result: ReleaseResult, from_ref: str, db_path: str = config.DB_PATH) -> int:
    created_at = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO releases
               (version, from_ref, created_at, readiness_score, recommendation,
                suggested_bump, internal_announcement, customer_notes, marketing_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.version,
                from_ref,
                created_at,
                result.readiness.score,
                result.readiness.recommendation,
                result.suggested_bump,
                result.internal_announcement,
                result.customer_notes,
                result.marketing_notes,
            ),
        )
        release_id = cur.lastrowid
        for row in result.traceability:
            jira_keys = json.dumps([t.key for t in row.jira_tickets])
            jira_statuses = json.dumps({t.key: t.status for t in row.jira_tickets})
            ci = row.ci_status
            conn.execute(
                """INSERT INTO traceability_rows
                   (release_id, short_hash, description, commit_type, is_breaking,
                    jira_keys, jira_statuses, pr_number, pr_url,
                    ci_total, ci_passed, ci_failed, ci_failed_names)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    release_id,
                    row.short_hash,
                    row.description,
                    row.commit_type,
                    1 if row.is_breaking else 0,
                    jira_keys,
                    jira_statuses,
                    row.pr_number,
                    row.pr_url,
                    ci.total if ci else None,
                    ci.passed if ci else None,
                    ci.failed if ci else None,
                    json.dumps(ci.failed_names) if ci else None,
                ),
            )
        conn.commit()
        return release_id


def get_release(version: str, db_path: str = config.DB_PATH) -> ReleaseResult | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM releases WHERE version = ?", (version,)).fetchone()
        if not row:
            return None
        rows = conn.execute(
            "SELECT * FROM traceability_rows WHERE release_id = ? ORDER BY id",
            (row["id"],),
        ).fetchall()
    traceability = []
    for r in rows:
        jira_keys = json.loads(r["jira_keys"])
        jira_statuses = json.loads(r["jira_statuses"])
        jira_tickets = [
            JiraTicket(
                key=k,
                summary="",
                status=jira_statuses.get(k, ""),
                issue_type="",
                priority=None,
            )
            for k in jira_keys
        ]
        ci = None
        if r["ci_total"] is not None:
            ci = CIStatus(
                total=r["ci_total"],
                passed=r["ci_passed"],
                failed=r["ci_failed"],
                failed_names=json.loads(r["ci_failed_names"] or "[]"),
            )
        traceability.append(
            TraceabilityRow(
                short_hash=r["short_hash"],
                description=r["description"],
                commit_type=r["commit_type"],
                is_breaking=bool(r["is_breaking"]),
                jira_tickets=jira_tickets,
                pr_number=r["pr_number"],
                pr_url=r["pr_url"],
                ci_status=ci,
            )
        )
    readiness = ReadinessReport(
        score=row["readiness_score"],
        recommendation=row["recommendation"],
        rationale="",
        risk_factors=[],
        rollback_plan="",
    )
    return ReleaseResult(
        version=row["version"],
        suggested_bump=row["suggested_bump"],
        readiness=readiness,
        internal_announcement=row["internal_announcement"],
        customer_notes=row["customer_notes"],
        traceability=traceability,
        marketing_notes=row["marketing_notes"],
    )


def list_releases(db_path: str = config.DB_PATH, limit: int = 20) -> list[ReleaseSummary]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT version, created_at, recommendation, readiness_score, suggested_bump
               FROM releases ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        ReleaseSummary(
            version=r["version"],
            created_at=r["created_at"],
            recommendation=r["recommendation"],
            readiness_score=r["readiness_score"],
            suggested_bump=r["suggested_bump"],
        )
        for r in rows
    ]


def release_exists(version: str, db_path: str = config.DB_PATH) -> bool:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT 1 FROM releases WHERE version = ?", (version,)).fetchone() is not None
