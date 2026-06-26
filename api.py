from __future__ import annotations
import asyncio
import json
import uuid
from typing import Optional
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI, BackgroundTasks
from release_pilot import config
from release_pilot.store import init_db, save_release, list_releases, get_release, release_exists
from release_pilot.git import get_commits
from release_pilot.parser import parse_commits
from release_pilot.semver import build_changeset
from release_pilot.models import (
    ReleaseResult, ReadinessReport, TraceabilityRow, JiraTicket, CIStatus, ReleaseSummary
)

# ── In-memory job store ─────────────────────────────────────────────────
jobs: dict[str, dict] = {}

# ── Strawberry type definitions ─────────────────────────────────────────

@strawberry.enum
class JobStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"

@strawberry.enum
class Recommendation:
    READY = "READY"
    HOLD = "HOLD"
    BLOCKED = "BLOCKED"

@strawberry.type
class JiraTicketGQL:
    key: str
    summary: str
    status: str
    issue_type: str
    priority: Optional[str]

@strawberry.type
class CIStatusGQL:
    total: int
    passed: int
    failed: int
    failed_names: list[str]

@strawberry.type
class TraceabilityRowGQL:
    short_hash: str
    description: str
    commit_type: str
    is_breaking: bool
    jira_tickets: list[JiraTicketGQL]
    pr_number: Optional[int]
    pr_url: Optional[str]
    ci_status: Optional[CIStatusGQL]

@strawberry.type
class ReadinessReportGQL:
    score: int
    recommendation: str
    rationale: str
    risk_factors: list[str]
    rollback_plan: str

@strawberry.type
class ReleaseResultGQL:
    version: str
    suggested_bump: str
    readiness: ReadinessReportGQL
    internal_announcement: str
    customer_notes: str
    marketing_notes: Optional[str]
    traceability: list[TraceabilityRowGQL]

@strawberry.type
class ReleaseSummaryGQL:
    version: str
    created_at: str
    recommendation: str
    readiness_score: int
    suggested_bump: str

@strawberry.type
class ReleaseJobGQL:
    job_id: str
    status: str
    result: Optional[ReleaseResultGQL] = None
    error: Optional[str] = None

@strawberry.input
class ReleaseInputGQL:
    version: str
    from_ref: str
    channel: str

# ── Converters ──────────────────────────────────────────────────────────

def _to_gql_result(r: ReleaseResult) -> ReleaseResultGQL:
    readiness = ReadinessReportGQL(
        score=r.readiness.score,
        recommendation=r.readiness.recommendation,
        rationale=r.readiness.rationale,
        risk_factors=r.readiness.risk_factors,
        rollback_plan=r.readiness.rollback_plan,
    )
    traceability = [
        TraceabilityRowGQL(
            short_hash=row.short_hash,
            description=row.description,
            commit_type=row.commit_type,
            is_breaking=row.is_breaking,
            jira_tickets=[JiraTicketGQL(key=t.key, summary=t.summary, status=t.status, issue_type=t.issue_type, priority=t.priority) for t in row.jira_tickets],
            pr_number=row.pr_number,
            pr_url=row.pr_url,
            ci_status=CIStatusGQL(total=row.ci_status.total, passed=row.ci_status.passed, failed=row.ci_status.failed, failed_names=row.ci_status.failed_names) if row.ci_status else None,
        )
        for row in r.traceability
    ]
    return ReleaseResultGQL(
        version=r.version,
        suggested_bump=r.suggested_bump,
        readiness=readiness,
        internal_announcement=r.internal_announcement,
        customer_notes=r.customer_notes,
        marketing_notes=r.marketing_notes,
        traceability=traceability,
    )

# ── Pipeline stub ────────────────────────────────────────────────────────

async def run_release_pipeline(job_id: str, version: str, from_ref: str, channel: str) -> None:
    """Runs the full release pipeline. coordinator.run() will be wired in Task 11."""
    jobs[job_id]["status"] = "RUNNING"
    try:
        commits = get_commits(from_ref=from_ref)
        parsed = parse_commits(commits)
        changeset = build_changeset(version, from_ref, parsed)

        # Placeholder result until coordinator is wired in Task 11
        from release_pilot.models import ReadinessReport, ReleaseResult
        placeholder_result = ReleaseResult(
            version=version,
            suggested_bump=changeset.suggested_bump,
            readiness=ReadinessReport(
                score=75,
                recommendation="HOLD",
                rationale="Pipeline stub — coordinator not yet wired.",
                risk_factors=["Coordinator not implemented yet"],
                rollback_plan="N/A",
            ),
            internal_announcement=f"[STUB] Release {version} triggered with {len(parsed)} commits.",
            customer_notes=f"[STUB] Customer notes for {version}.",
            traceability=[],
        )

        jobs[job_id]["status"] = "DONE"
        jobs[job_id]["result"] = placeholder_result

        if not release_exists(version):
            save_release(placeholder_result, from_ref)
    except Exception as e:
        jobs[job_id]["status"] = "ERROR"
        jobs[job_id]["error"] = str(e)

# ── GraphQL schema ────────────────────────────────────────────────────────

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def trigger_release(self, input: ReleaseInputGQL, info: strawberry.types.Info) -> ReleaseJobGQL:
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "PENDING", "result": None, "error": None}
        background_tasks: BackgroundTasks = info.context["background_tasks"]
        background_tasks.add_task(run_release_pipeline, job_id, input.version, input.from_ref, input.channel)
        return ReleaseJobGQL(job_id=job_id, status="PENDING")

@strawberry.type
class Query:
    @strawberry.field
    def release_status(self, job_id: str) -> ReleaseJobGQL:
        job = jobs.get(job_id)
        if not job:
            return ReleaseJobGQL(job_id=job_id, status="ERROR", error="Job not found")
        result_gql = _to_gql_result(job["result"]) if job.get("result") else None
        return ReleaseJobGQL(
            job_id=job_id,
            status=job["status"],
            result=result_gql,
            error=job.get("error"),
        )

    @strawberry.field
    def release_history(self, limit: int = 20) -> list[ReleaseSummaryGQL]:
        summaries = list_releases(limit=limit)
        return [ReleaseSummaryGQL(
            version=s.version, created_at=s.created_at,
            recommendation=s.recommendation, readiness_score=s.readiness_score,
            suggested_bump=s.suggested_bump,
        ) for s in summaries]

    @strawberry.field
    def release(self, version: str) -> Optional[ReleaseResultGQL]:
        r = get_release(version)
        return _to_gql_result(r) if r else None

# ── FastAPI app ───────────────────────────────────────────────────────────

schema = strawberry.Schema(query=Query, mutation=Mutation)

async def get_context(background_tasks: BackgroundTasks):
    return {"background_tasks": background_tasks}

graphql_router = GraphQLRouter(schema, context_getter=get_context)

app = FastAPI(title="release-pilot")
app.include_router(graphql_router, prefix="/graphql")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}
