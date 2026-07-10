from __future__ import annotations

import pytest

from release_pilot.models import (
    CIStatus,
    CommitInfo,
    JiraTicket,
    ReadinessReport,
    ReleaseResult,
    TraceabilityRow,
)


@pytest.fixture
def sample_commit_infos() -> list[CommitInfo]:
    return [
        CommitInfo(
            hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            short_hash="a1b2c3d",
            author="Kenji Watanabe",
            date="2026-06-20T09:14:00+09:00",
            subject="feat(picking): add vision-guided pick confirmation (NYANKO-456)",
            body="NYANKO-456",
        ),
        CommitInfo(
            hash="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
            short_hash="b2c3d4e",
            author="Sara Chen",
            date="2026-06-20T11:30:00+09:00",
            subject="feat(api)!: rename /api/v1/robot-status to /api/v2/status (NYANKO-789)",
            body=(
                "BREAKING CHANGE: /api/v1/robot-status is removed. Clients must migrate "
                "to /api/v2/status.\nNYANKO-789"

            ),
        ),
        CommitInfo(
            hash="c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
            short_hash="c3d4e5f",
            author="Tomas Rivera",
            date="2026-06-21T14:05:00+09:00",
            subject="fix(palletizing): resolve stack overflow (NYANKO-234)",
            body="NYANKO-234",
        ),
        CommitInfo(
            hash="d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
            short_hash="d4e5f6a",
            author="Yuki Tanaka",
            date="2026-06-22T10:00:00+09:00",
            subject="chore(ci): upgrade GitHub Actions runners",
            body="",
        ),
    ]


@pytest.fixture
def sample_release_result() -> ReleaseResult:
    readiness = ReadinessReport(
        score=82,
        recommendation="READY",
        rationale="All checks pass on customer-facing commits.",
        risk_factors=["Minor: one chore commit lacks CI evidence"],
        rollback_plan="Revert to v2.2.0 tag.",
    )
    traceability = [
        TraceabilityRow(
            short_hash="a1b2c3d",
            description="add vision-guided pick confirmation",
            commit_type="feat",
            is_breaking=False,
            jira_tickets=[
                JiraTicket(
                    key="NYANKO-456",
                    summary="Vision pick confirm",
                    status="Done",
                    issue_type="Story",
                    priority="High",
                )
            ],
            pr_number=45,
            pr_url="https://github.com/nyanko/nyankoos/pull/45",
            ci_status=CIStatus(total=14, passed=14, failed=0),
        ),
        TraceabilityRow(
            short_hash="b2c3d4e",
            description="rename /api/v1/robot-status to /api/v2/status",
            commit_type="feat",
            is_breaking=True,
            jira_tickets=[
                JiraTicket(
                    key="NYANKO-789",
                    summary="API versioning",
                    status="Done",
                    issue_type="Task",
                    priority="High",
                )
            ],
            pr_number=46,
            pr_url="https://github.com/nyanko/nyankoos/pull/46",
            ci_status=CIStatus(
                total=14,
                passed=12,
                failed=2,
                failed_names=[
                    "integration/api-backward-compat",
                    "integration/client-sdk-v1",
                ],
            ),
        ),
    ]
    return ReleaseResult(
        version="v2.3.0",
        suggested_bump="major",
        readiness=readiness,
        internal_announcement="NyankoOS v2.3.0 is released.",
        customer_notes="## What's New\n\n- Vision-guided pick confirmation.",
        marketing_notes="NyankoOS v2.3.0 delivers faster picking.",
        traceability=traceability,
    )


@pytest.fixture
def tmp_db(tmp_path) -> str:
    return str(tmp_path / "test.db")
