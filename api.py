from __future__ import annotations

import json
import uuid
from enum import Enum

import strawberry
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from strawberry.fastapi import GraphQLRouter

from release_pilot.git import get_commits
from release_pilot.models import ReleaseResult
from release_pilot.parser import parse_commits
from release_pilot.semver import build_changeset
from release_pilot.store import (
    get_release,
    init_db,
    list_releases,
    release_exists,
    save_release,
)

# ── In-memory job store ─────────────────────────────────────────────────
jobs: dict[str, dict] = {}

# ── Strawberry type definitions ─────────────────────────────────────────


@strawberry.enum
class JobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


@strawberry.enum
class Recommendation(Enum):
    READY = "READY"
    HOLD = "HOLD"
    BLOCKED = "BLOCKED"


@strawberry.type
class JiraTicketGQL:
    key: str
    summary: str
    status: str
    issue_type: str
    priority: str | None


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
    pr_number: int | None
    pr_url: str | None
    ci_status: CIStatusGQL | None


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
    marketing_notes: str | None
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
    result: ReleaseResultGQL | None = None
    error: str | None = None


@strawberry.input
class ReleaseInputGQL:
    version: str
    from_ref: str
    channel: str
    thread_ts: str | None = None


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
            jira_tickets=[
                JiraTicketGQL(
                    key=t.key,
                    summary=t.summary,
                    status=t.status,
                    issue_type=t.issue_type,
                    priority=t.priority,
                )
                for t in row.jira_tickets
            ],
            pr_number=row.pr_number,
            pr_url=row.pr_url,
            ci_status=CIStatusGQL(
                total=row.ci_status.total,
                passed=row.ci_status.passed,
                failed=row.ci_status.failed,
                failed_names=row.ci_status.failed_names,
            )
            if row.ci_status
            else None,
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


# ── Pipeline ─────────────────────────────────────────────────────────────


async def run_release_pipeline(
    job_id: str, version: str, from_ref: str, channel: str, thread_ts: str | None = None
) -> None:
    """Runs the full release pipeline via coordinator."""
    import logging

    log = logging.getLogger(__name__)
    jobs[job_id]["status"] = "RUNNING"
    try:
        from release_pilot.coordinator import run as coordinator_run

        log.info(f"[{version}] building changeset")
        commits = get_commits(from_ref=from_ref)
        parsed = parse_commits(commits)
        changeset = build_changeset(version, from_ref, parsed)
        log.info(f"[{version}] changeset ready: {len(changeset.commits)} commits")

        from slack_sdk import WebClient as SlackClient

        from release_pilot import config as release_config

        slack_client = SlackClient(token=release_config.SLACK_BOT_TOKEN)

        def post_progress(msg: str):
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=msg,
                mrkdwn=True,
            )

        log.info(f"[{version}] starting coordinator")
        result = await coordinator_run(changeset, progress_cb=post_progress)
        log.info(f"[{version}] coordinator done")

        jobs[job_id]["status"] = "DONE"
        jobs[job_id]["result"] = result

        # Post to Slack before DB write so failures don't block delivery
        from release_pilot.slack_poster import post_all as slack_post_all

        slack_post_all(result, channel, release_config.SLACK_BOT_TOKEN, thread_ts=thread_ts)

        try:
            if not release_exists(version):
                save_release(result, from_ref)
        except Exception as db_err:
            import logging

            logging.getLogger(__name__).warning(f"DB save failed (non-fatal): {db_err}")

        # Prompt user to generate PDF
        slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"📄 Generate a PDF of the {version} release notes?",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📄 Would you like to generate a *PDF* of the *{version}* release notes?",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Yes, generate PDF",
                            },
                            "style": "primary",
                            "action_id": "generate_pdf",
                            "value": json.dumps(
                                {
                                    "version": version,
                                    "channel": channel,
                                    "thread_ts": thread_ts,
                                }
                            ),
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "No thanks"},
                            "action_id": "skip_pdf",
                            "value": "skip",
                        },
                    ],
                },
            ],
        )

    except Exception as e:
        import traceback

        jobs[job_id]["status"] = "ERROR"
        jobs[job_id]["error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        try:
            from slack_sdk import WebClient as _SlackClient

            from release_pilot import config as release_config

            _SlackClient(token=release_config.SLACK_BOT_TOKEN).chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"❌ Pipeline failed: `{type(e).__name__}: {e}`",
            )
        except Exception:
            pass


# ── GraphQL schema ────────────────────────────────────────────────────────


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def trigger_release(
        self, input: ReleaseInputGQL, info: strawberry.types.Info
    ) -> ReleaseJobGQL:
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "PENDING", "result": None, "error": None}
        background_tasks: BackgroundTasks = info.context["background_tasks"]
        background_tasks.add_task(
            run_release_pipeline,
            job_id,
            input.version,
            input.from_ref,
            input.channel,
            input.thread_ts,
        )
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
        return [
            ReleaseSummaryGQL(
                version=s.version,
                created_at=s.created_at,
                recommendation=s.recommendation,
                readiness_score=s.readiness_score,
                suggested_bump=s.suggested_bump,
            )
            for s in summaries
        ]

    @strawberry.field
    def release(self, version: str) -> ReleaseResultGQL | None:
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
    from release_pilot.seed import seed_releases

    seeded = seed_releases()
    if seeded:
        import logging

        logging.getLogger(__name__).info(f"Seeded {seeded} historical releases")


@app.get("/releases", response_class=HTMLResponse)
def releases_index():
    from pathlib import Path

    from release_pilot import config as release_config

    pdf_dir = Path(release_config.PDF_DIR)

    summaries = list_releases(limit=50)
    rows = ""
    for s in summaries:
        badge = {"READY": "🟢", "HOLD": "🟡", "BLOCKED": "🔴"}.get(s.recommendation, "⚪")
        pdf_exists = (pdf_dir / f"{s.version}.pdf").exists()
        pdf_link = (
            f'<a href="/releases/{s.version}.pdf" title="Download PDF">📄 PDF</a>'
            if pdf_exists
            else '<span style="color:#aaa">—</span>'
        )
        rows += (
            f"<tr>"
            f'<td><a href="/releases/{s.version}">{s.version}</a></td>'
            f"<td>{s.created_at[:10]}</td>"
            f"<td>{badge} {s.recommendation}</td>"
            f"<td>{s.readiness_score}/100</td>"
            f"<td>{s.suggested_bump}</td>"
            f'<td><a href="/releases/{s.version}.md">⬇ .md</a></td>'
            f"<td>{pdf_link}</td>"
            f"</tr>\n"
        )
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Release Notes — release-pilot</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; color: #222; }}
    h1 {{ font-size: 1.6rem; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th {{ text-align: left; padding: 8px 12px; background: #f5f5f5; border-bottom: 2px solid #ddd; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
    tr:hover td {{ background: #fafafa; }}
    a {{ color: #0066cc; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>🚀 Release Notes</h1>
  <table>
    <thead><tr><th>Version</th><th>Released</th><th>Status</th><th>Readiness</th><th>Bump</th><th>Markdown</th><th>PDF</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>"""


# ── IMPORTANT: specific extension routes must come BEFORE the bare {version} route ──


@app.get("/releases/{version}.md", response_class=PlainTextResponse)
def release_markdown(version: str):
    r = get_release(version)
    if not r:
        return PlainTextResponse("Release not found", status_code=404)
    marketing_section = (
        f"\n\n---\n\n## Marketing Notes\n\n{r.marketing_notes}" if r.marketing_notes else ""
    )
    internal_section = (
        f"\n\n---\n\n## Internal Announcement\n\n{r.internal_announcement}"
        if r.internal_announcement
        else ""
    )
    return f"""# {r.version} Release Notes

> **Readiness:** {r.readiness.recommendation} | **Score:** {r.readiness.score}/100 | **Bump:** {r.suggested_bump}

---

{r.customer_notes}{marketing_section}{internal_section}
""".strip()


@app.get("/releases/{version}.pdf")
def release_pdf(version: str):
    from pathlib import Path

    from fastapi import HTTPException

    from release_pilot import config as release_config

    pdf_path = Path(release_config.PDF_DIR) / f"{version}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found — generate it first")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"release-notes-{version}.pdf",
    )


@app.post("/releases/{version}/generate-pdf")
def generate_pdf(version: str):
    from pathlib import Path

    from release_pilot import config as release_config
    from release_pilot.pdf_gen import generate as gen_pdf

    r = get_release(version)
    if not r:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Release not found")

    pdf_dir = Path(release_config.PDF_DIR)
    out_path = pdf_dir / f"{version}.pdf"

    gen_pdf(
        version=r.version,
        customer_notes=r.customer_notes,
        marketing_notes=r.marketing_notes,
        internal_announcement=r.internal_announcement,
        readiness_score=r.readiness.score,
        recommendation=r.readiness.recommendation,
        suggested_bump=r.suggested_bump,
        output_path=out_path,
    )

    url = f"{release_config.WEB_BASE_URL}/releases/{version}.pdf"
    return {"url": url, "version": version}


@app.get("/releases/{version}", response_class=HTMLResponse)
def release_detail(version: str):
    from pathlib import Path

    from release_pilot import config as release_config

    r = get_release(version)
    if not r:
        return HTMLResponse("<h2>Release not found</h2>", status_code=404)

    pdf_exists = (Path(release_config.PDF_DIR) / f"{version}.pdf").exists()
    pdf_button = (
        f'<a class="dl-btn" href="/releases/{version}.pdf">📄 Download PDF</a>'
        if pdf_exists
        else ""
    )

    customer_md = r.customer_notes or "_No customer notes generated._"
    marketing_md = r.marketing_notes or "_No marketing notes generated._"
    internal_md = r.internal_announcement or "_No internal announcement generated._"

    rec = r.readiness.recommendation
    badge_color = {"READY": "#0a8a45", "HOLD": "#b8860b", "BLOCKED": "#c0392b"}.get(rec, "#555")

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{version} — release-pilot</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
    nav {{ margin-bottom: 16px; font-size: 0.9rem; }}
    nav a {{ color: #0066cc; text-decoration: none; }}
    .header-row {{ display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 4px; }}
    h1 {{ font-size: 1.8rem; margin: 0; }}
    .meta {{ font-size: 0.88rem; color: #555; margin-bottom: 18px; }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 700; color: #fff; background: {badge_color}; margin-left: 8px; vertical-align: middle; }}
    .dl-row {{ display: flex; gap: 8px; font-size: 0.88rem; flex-shrink: 0; }}
    .dl-btn {{ color: #0066cc; text-decoration: none; border: 1px solid #0066cc; padding: 4px 10px; border-radius: 4px; white-space: nowrap; }}
    .dl-btn:hover {{ background: #0066cc; color: #fff; }}
    /* Tabs */
    .tabs {{ display: flex; border-bottom: 2px solid #ddd; margin-bottom: 24px; gap: 0; }}
    .tab-btn {{ padding: 8px 20px; border: none; background: none; cursor: pointer; font-size: 0.95rem; color: #555; border-bottom: 3px solid transparent; margin-bottom: -2px; transition: color .15s; }}
    .tab-btn:hover {{ color: #222; }}
    .tab-btn.active {{ color: #0066cc; border-bottom-color: #0066cc; font-weight: 600; }}
    .tab-pane {{ display: none; }}
    .tab-pane.active {{ display: block; }}
    /* Content styles */
    h2 {{ font-size: 1.25rem; border-bottom: 1px solid #eee; padding-bottom: 6px; margin-top: 28px; }}
    h3 {{ font-size: 1.05rem; margin-top: 20px; }}
    hr {{ border: none; border-top: 1px solid #eee; margin: 24px 0; }}
    code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-size: 0.87em; }}
    pre {{ background: #f4f4f4; padding: 14px; border-radius: 6px; overflow-x: auto; }}
    ul {{ padding-left: 20px; }} li {{ margin: 4px 0; }}
    a {{ color: #0066cc; }}
    .internal-banner {{ background: #fff8e1; border-left: 4px solid #f0a500; padding: 8px 14px; border-radius: 4px; font-size: 0.85rem; color: #7a5800; margin-bottom: 16px; }}
  </style>
</head>
<body>
  <nav><a href="/releases">← All Releases</a></nav>
  <div class="header-row">
    <h1>{version} <span class="badge">{rec}</span></h1>
    <div class="dl-row">
      <a class="dl-btn" href="/releases/{version}.md">⬇ .md</a>
      {pdf_button}
    </div>
  </div>
  (
    '<div class="meta">'
    f"Readiness score: {r.readiness.score}/100 "
    "&nbsp;·&nbsp; "
    f"Suggested bump: {r.suggested_bump}"
    "</div>"
  )

  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('customer', this)">📋 Customer</button>
    <button class="tab-btn" onclick="showTab('marketing', this)">📣 Marketing</button>
    <button class="tab-btn" onclick="showTab('internal', this)">🔒 Internal</button>
  </div>

  <div id="tab-customer" class="tab-pane active"></div>
  <div id="tab-marketing" class="tab-pane"></div>
  <div id="tab-internal" class="tab-pane">
    <div class="internal-banner">⚠️ Internal use only — not for external distribution</div>
    <div id="tab-internal-content"></div>
  </div>

  <script>
    function showTab(name, btn) {{
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      btn.classList.add('active');
    }}
    const customer = {repr(customer_md)};
    const marketing = {repr(marketing_md)};
    const internal_ = {repr(internal_md)};
    document.getElementById('tab-customer').innerHTML = marked.parse(customer);
    document.getElementById('tab-marketing').innerHTML = marked.parse(marketing);
    document.getElementById('tab-internal-content').innerHTML = marked.parse(internal_);
  </script>
</body>
</html>"""


@app.get("/health")
def health():
    return {"status": "ok"}
