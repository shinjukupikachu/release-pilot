from __future__ import annotations

import asyncio
import json

import anthropic as _anthropic

from release_pilot import config as _config
from release_pilot.agents.base import AgentDefinition
from release_pilot.agents.breaking_change_agent import BREAKING_CHANGE_AGENT
from release_pilot.agents.classifier_agent import CLASSIFIER_AGENT
from release_pilot.agents.customer_notes_agent import CUSTOMER_NOTES_AGENT
from release_pilot.agents.github_enrichment_agent import GITHUB_ENRICHMENT_AGENT
from release_pilot.agents.jira_enrichment_agent import JIRA_ENRICHMENT_AGENT
from release_pilot.agents.marketing_notes_agent import MARKETING_NOTES_AGENT
from release_pilot.agents.readiness_agent import READINESS_AGENT
from release_pilot.models import (
    ChangeSet,
    CIStatus,
    JiraTicket,
    ReadinessReport,
    ReleaseResult,
    TraceabilityRow,
)


def _llm_label() -> str:
    """Human-readable label for whichever LLM backend is active."""
    if _config.KIMI_API_KEY:
        return f"Kimi ({_config.KIMI_MODEL})"
    if _config.ANTHROPIC_API_KEY:
        return "Claude (Anthropic)"
    return "LLM (stub)"


async def run(changeset: ChangeSet, progress_cb=None) -> ReleaseResult:
    """Three-phase async pipeline. Phase 0: enrichment. Phase 1: classify +
       readiness. Phase 2: notes.

    TEST_DATA=1 mocks only Phase 0 (Jira + GitHub fixtures); Phases 1 & 2 still call the LLM.
    progress_cb(msg): optional callable that posts status updates to Slack.
    """

    def _post(msg: str):
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    llm = _llm_label()
    n = len(changeset.commits)

    # ── Phase 0: enrichment ───────────────────────────────────────────────
    if _config.TEST_DATA:
        _post(f"⚙️ *Phase 0* — Loading {n} commits + Jira & GitHub data from test fixtures")
        jira_result, github_result = _load_enrichment_from_test_data()
    else:
        _post(f"⚙️ *Phase 0* — Fetching Jira tickets & GitHub PR/CI data for {n} commits via MCP")
        all_jira_keys = list({k for c in changeset.commits for k in c.jira_keys})
        all_shas = [c.hash for c in changeset.commits]
        jira_result, github_result = await asyncio.gather(
            _run_agent(JIRA_ENRICHMENT_AGENT, json.dumps({"jira_keys": all_jira_keys})),
            _run_agent(GITHUB_ENRICHMENT_AGENT, json.dumps({"commit_shas": all_shas})),
        )

    enriched = _merge_enrichment(changeset, jira_result, github_result)

    # ── Phase 1: classify + readiness (parallel) ──────────────────────────
    _post(f"🤖 *Phase 1* — Running 2 AI agents in parallel via *{llm}*\n   • *Classifier*: labelling {n} commits by audience & breaking-change status\n   • *Readiness*: scoring release risk from CI failures & open Jira tickets")

    classify_input = _build_classify_input(enriched)
    readiness_input = _build_readiness_input(enriched)

    classify_result, readiness_result = await asyncio.gather(
        _run_agent(CLASSIFIER_AGENT, classify_input),
        _run_agent(READINESS_AGENT, readiness_input),
    )

    audience_map = {c["short_hash"]: c["audience"] for c in classify_result.get("commits", [])}
    for commit in enriched.commits:
        commit.audience = audience_map.get(commit.short_hash, "internal")

    customer_commits = [c for c in enriched.commits if c.audience in ("customer", "marketing")]
    marketing_commits = [c for c in enriched.commits if c.audience == "marketing"]
    # Fall back to top customer commits when no marketing-tier commits were classified
    marketing_source = marketing_commits if marketing_commits else customer_commits[:5]
    n_breaking = len(enriched.breaking)

    # ── Phase 2: notes generation (parallel) ──────────────────────────────
    marketing_label = f"{len(marketing_commits)} headline features" if marketing_commits else f"top {len(marketing_source)} customer highlights (no marketing-tier commits)"
    phase2_agents = [
        (f"• *Customer Notes*: drafting release notes for {len(customer_commits)} customer-facing commits"),
        (f"• *Marketing Notes*: writing copy for {marketing_label}"),
    ]
    if enriched.breaking:
        phase2_agents.append(f"• *Breaking Change*: documenting migration steps for {n_breaking} breaking commit(s)")

    _post(f"🤖 *Phase 2* — Running {len(phase2_agents)} AI agents in parallel via *{llm}*\n" + "\n".join(f"   {a}" for a in phase2_agents))

    phase2_coros = [
        _run_agent(
            CUSTOMER_NOTES_AGENT,
            _build_notes_input(customer_commits, enriched.version, "customer"),
        ),
        _run_agent(
            MARKETING_NOTES_AGENT,
            _build_notes_input(marketing_source, enriched.version, "marketing"),
        ),
    ]
    if enriched.breaking:
        phase2_coros.append(_run_agent(BREAKING_CHANGE_AGENT, _build_breaking_input(enriched.breaking)))

    phase2_results = await asyncio.gather(*phase2_coros)
    customer_result = phase2_results[0]
    marketing_result = phase2_results[1]
    breaking_result = phase2_results[2] if len(phase2_results) > 2 else None

    _post("✅ *All agents complete* — compiling results...")

    # ── Build final result ─────────────────────────────────────────────────
    return _build_release_result(
        enriched,
        classify_result,
        readiness_result,
        customer_result,
        marketing_result,
        breaking_result,
    )


def _load_enrichment_from_test_data() -> tuple[dict, dict]:
    """Load Jira + GitHub fixture files and normalise into the shape _merge_enrichment expects."""
    jira_raw = json.loads((_config.TEST_DATA_DIR / "jira_issues.json").read_text())
    prs_raw = json.loads((_config.TEST_DATA_DIR / "github_prs.json").read_text())
    ci_raw = json.loads((_config.TEST_DATA_DIR / "github_check_runs.json").read_text())

    # Normalise Jira: {key: {fields: {summary, status: {name}, issuetype: {name},
    # priority: {name}}}}
    # → {key: {key, summary, status, issue_type, priority}}
    issues = {}
    for key, raw in jira_raw.items():
        fields = raw.get("fields", {})
        issues[key] = {
            "key": key,
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "issue_type": fields.get("issuetype", {}).get("name", "Unknown"),
            "priority": fields.get("priority", {}).get("name"),
        }

    # Normalise GitHub PRs: {hash: {number, title, html_url, user: {login}}}
    # → {hash: {number, title, url}}
    prs = {}
    for sha, pr in prs_raw.items():
        prs[sha] = {
            "number": pr.get("number"),
            "title": pr.get("title", ""),
            "url": pr.get("html_url", ""),
        }

    return {"issues": issues}, {"prs": prs, "check_runs": ci_raw}


def _load_test_result(changeset: ChangeSet) -> ReleaseResult:
    """Return a fully pre-baked ReleaseResult from test_data/release_result.json."""
    data = json.loads((_config.TEST_DATA_DIR / "release_result.json").read_text())
    classify = data["classify"]
    readiness_data = data["readiness"]
    jira_data = json.loads((_config.TEST_DATA_DIR / "jira_issues.json").read_text())
    github_prs = json.loads((_config.TEST_DATA_DIR / "github_prs.json").read_text())
    github_ci = json.loads((_config.TEST_DATA_DIR / "github_check_runs.json").read_text())

    audience_map = {c["short_hash"]: c["audience"] for c in classify["commits"]}
    traceability = []
    for commit in changeset.commits:
        commit.audience = audience_map.get(commit.short_hash, "internal")
        jira_tickets = []
        for key in commit.jira_keys:
            issue = jira_data.get("issues", {}).get(key, {})
            if issue and "error" not in issue:
                jira_tickets.append(
                    JiraTicket(
                        key=issue.get("key", key),
                        summary=issue.get("summary", ""),
                        status=issue.get("status", "Unknown"),
                        issue_type=issue.get("issue_type", "Unknown"),
                        priority=issue.get("priority"),
                    )
                )
        pr = github_prs.get("prs", {}).get(commit.hash, {})
        ci = github_ci.get("check_runs", {}).get(commit.hash, {})
        ci_status = (
            CIStatus(
                total=ci.get("total", 0),
                passed=ci.get("passed", 0),
                failed=ci.get("failed", 0),
                failed_names=ci.get("failed_names", []),
            )
            if ci.get("total", 0) > 0
            else None
        )
        traceability.append(
            TraceabilityRow(
                short_hash=commit.short_hash,
                description=commit.clean_subject,
                commit_type=commit.commit_type,
                is_breaking=commit.is_breaking,
                jira_tickets=jira_tickets,
                pr_number=pr.get("number") if pr else None,
                pr_url=pr.get("url") if pr else None,
                ci_status=ci_status,
            )
        )

    # Substitute the hardcoded template version with the actual requested version
    version = changeset.version

    def _vsub(text: str | None) -> str | None:
        return text.replace("v2.3.0", version).replace("2.3.0", version.lstrip("v")) if text else text

    return ReleaseResult(
        version=version,
        suggested_bump=changeset.suggested_bump,
        readiness=ReadinessReport(
            score=readiness_data["score"],
            recommendation=readiness_data["recommendation"],
            rationale=_vsub(readiness_data["rationale"]),
            risk_factors=[_vsub(r) for r in readiness_data["risk_factors"]],
            rollback_plan=_vsub(readiness_data["rollback_plan"]),
        ),
        internal_announcement=_vsub(classify["internal_announcement"]),
        customer_notes=_vsub(data["customer_notes"]["customer_notes"]),
        marketing_notes=_vsub(data["marketing_notes"]["marketing_notes"]),
        traceability=traceability,
    )


def _merge_enrichment(changeset: ChangeSet, jira_result: dict, github_result: dict) -> ChangeSet:
    """Attach Jira tickets and GitHub PR/CI data to each commit."""
    jira_issues = jira_result.get("issues", {})
    prs = github_result.get("prs", {})
    check_runs = github_result.get("check_runs", {})

    for commit in changeset.commits:
        # Jira tickets
        commit.jira_tickets = []
        for key in commit.jira_keys:
            issue = jira_issues.get(key, {})
            if issue and "error" not in issue:
                commit.jira_tickets.append(
                    JiraTicket(
                        key=issue.get("key", key),
                        summary=issue.get("summary", ""),
                        status=issue.get("status", "Unknown"),
                        issue_type=issue.get("issue_type", "Unknown"),
                        priority=issue.get("priority"),
                    )
                )

        # GitHub PR
        pr = prs.get(commit.hash, {})
        if pr and pr.get("number") is not None:
            commit.pr_number = pr.get("number")
            commit.pr_url = pr.get("url")
            commit.pr_title = pr.get("title")

        # CI status
        ci = check_runs.get(commit.hash, {})
        if ci and ci.get("total", 0) > 0:
            commit.ci_status = CIStatus(
                total=ci.get("total", 0),
                passed=ci.get("passed", 0),
                failed=ci.get("failed", 0),
                failed_names=ci.get("failed_names", []),
            )

    changeset.breaking = [c for c in changeset.commits if c.is_breaking]
    return changeset


def _build_classify_input(changeset: ChangeSet) -> str:
    lines = [f"version: {changeset.version}", "commits:"]
    for c in changeset.commits:
        jira_str = " ".join(f"[{t.key} {t.status} {t.issue_type}]" for t in c.jira_tickets) or "none"
        pr_str = f"#{c.pr_number}" if c.pr_number else "none"
        if c.ci_status:
            ci_str = f"{c.ci_status.passed}/{c.ci_status.total} passed"
            if c.ci_status.failed:
                ci_str += f" (FAILED: {', '.join(c.ci_status.failed_names)})"
        else:
            ci_str = "no CI data"
        breaking_flag = " BREAKING" if c.is_breaking else ""
        scope_str = f"({c.scope})" if c.scope else ""
        lines.append(f"  - {c.short_hash} | {c.commit_type}{scope_str}{breaking_flag} | {c.clean_subject}")
        lines.append(f"    jira: {jira_str} | pr: {pr_str} | ci: {ci_str}")
    return "\n".join(lines)


def _build_readiness_input(changeset: ChangeSet) -> str:
    return _build_classify_input(changeset)  # same input shape


def _build_notes_input(commits: list, version: str, audience: str) -> str:
    if not commits:
        return json.dumps({"version": version, "commits": [], "audience": audience})
    return json.dumps(
        {
            "version": version,
            "audience": audience,
            "commits": [
                {
                    "short_hash": c.short_hash,
                    "type": c.commit_type,
                    "scope": c.scope,
                    "is_breaking": c.is_breaking,
                    "subject": c.clean_subject,
                    "breaking_note": c.breaking_note,
                    "jira_tickets": [{"key": t.key, "summary": t.summary, "status": t.status} for t in c.jira_tickets],
                }
                for c in commits
            ],
        }
    )


def _build_breaking_input(breaking_commits: list) -> str:
    return json.dumps(
        {
            "breaking_commits": [
                {
                    "short_hash": c.short_hash,
                    "subject": c.clean_subject,
                    "breaking_note": c.breaking_note,
                    "scope": c.scope,
                }
                for c in breaking_commits
            ]
        }
    )


def _extract_json(text: str) -> dict:
    """Brace-matching scanner: find the first balanced {...} block in text."""
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in agent output: {text[:200]!r}")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"Unbalanced braces in agent output: {text[:200]!r}")


def _validate_output(description: str, result: dict, required_keys: list[str]) -> dict:
    missing = [k for k in required_keys if k not in result]
    if missing:
        raise ValueError(f"Agent '{description}' output missing keys: {missing}")
    return result


async def _run_agent(agent_def: AgentDefinition, user_msg: str) -> dict:
    """Invoke one agent. Uses Kimi if KIMI_API_KEY is set, otherwise Anthropic."""
    if agent_def.tools:
        return _stub_response(agent_def.description)

    if not _config.KIMI_API_KEY and not _config.ANTHROPIC_API_KEY:
        raise RuntimeError("No LLM API key configured. Set KIMI_API_KEY or ANTHROPIC_API_KEY.")

    coro = _run_agent_kimi(agent_def, user_msg) if _config.KIMI_API_KEY else _run_agent_anthropic(agent_def, user_msg)
    try:
        return await asyncio.wait_for(coro, timeout=60.0)
    except TimeoutError as err:
        raise RuntimeError(f"Agent '{agent_def.description}' timed out after 60s") from err


async def _run_agent_kimi(agent_def: AgentDefinition, user_msg: str) -> dict:
    import logging

    import httpx
    from openai import AsyncOpenAI

    log = logging.getLogger(__name__)
    log.info(f"kimi call start: {agent_def.description[:60]}")
    client = AsyncOpenAI(
        api_key=_config.KIMI_API_KEY,
        base_url=_config.KIMI_BASE_URL,
        http_client=httpx.AsyncClient(timeout=55.0),
    )
    response = await client.chat.completions.create(
        model=_config.KIMI_MODEL,
        max_tokens=6000,
        messages=[
            {"role": "system", "content": agent_def.prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    raw = response.choices[0].message.content or ""
    log.info(f"kimi call done: {agent_def.description[:60]}, response len={len(raw)}")
    return _extract_json(raw)


async def _run_agent_anthropic(agent_def: AgentDefinition, user_msg: str) -> dict:
    client = _anthropic.AsyncAnthropic(api_key=_config.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=agent_def.prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = "".join(block.text for block in response.content if hasattr(block, "text"))
    return _extract_json(raw)


def _stub_response(description: str) -> dict:
    """Fallback stub when SDK not installed — returns plausible empty structure."""
    if "classifier" in description.lower() or "classify" in description.lower():
        return {
            "commits": [],
            "internal_announcement": "[SDK not installed — stub output]",
        }
    if "readiness" in description.lower():
        return {
            "score": 75,
            "recommendation": "HOLD",
            "rationale": "SDK not installed",
            "risk_factors": ["claude_agent_sdk not installed"],
            "rollback_plan": "N/A",
            "per_commit_risk": [],
        }
    if "customer" in description.lower():
        return {"customer_notes": "[SDK not installed — stub output]"}
    if "marketing" in description.lower():
        return {"marketing_notes": None}
    if "breaking" in description.lower():
        return {
            "affected_components": [],
            "severity": "UNKNOWN",
            "migration_steps": [],
            "customer_action_required": False,
        }
    if "jira" in description.lower():
        return {"issues": {}}
    if "github" in description.lower():
        return {"prs": {}, "check_runs": {}}
    return {}


def _build_release_result(
    enriched: ChangeSet,
    classify_result: dict,
    readiness_result: dict,
    customer_result: dict,
    marketing_result: dict,
    breaking_result: dict | None,
) -> ReleaseResult:
    readiness = ReadinessReport(
        score=readiness_result.get("score", 75),
        recommendation=readiness_result.get("recommendation", "HOLD"),
        rationale=readiness_result.get("rationale", ""),
        risk_factors=readiness_result.get("risk_factors", []),
        rollback_plan=readiness_result.get("rollback_plan", ""),
    )

    traceability = []
    for commit in enriched.commits:
        ci = commit.ci_status
        traceability.append(
            TraceabilityRow(
                short_hash=commit.short_hash,
                description=commit.clean_subject,
                commit_type=commit.commit_type,
                is_breaking=commit.is_breaking,
                jira_tickets=commit.jira_tickets,
                pr_number=commit.pr_number,
                pr_url=commit.pr_url,
                ci_status=ci,
            )
        )

    return ReleaseResult(
        version=enriched.version,
        suggested_bump=enriched.suggested_bump,
        readiness=readiness,
        internal_announcement=classify_result.get("internal_announcement", ""),
        customer_notes=customer_result.get("customer_notes", ""),
        marketing_notes=marketing_result.get("marketing_notes"),
        traceability=traceability,
    )
