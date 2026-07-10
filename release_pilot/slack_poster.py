from __future__ import annotations

import os

from release_pilot.models import ReleaseResult

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    _SLACK_AVAILABLE = True
except ImportError:
    _SLACK_AVAILABLE = False
    WebClient = None
    SlackApiError = Exception


def _ci_emoji(ci) -> str:
    if not ci:
        return "—"
    if ci.failed == 0:
        return f"✅ {ci.passed}/{ci.total}"
    return f"⚠️ {ci.passed}/{ci.total} (FAILED: {', '.join(ci.failed_names)})"


def _build_traceability_table(result: ReleaseResult) -> str:
    lines = [
        "| Commit | Description | Jira | PR | CI |",
        "|--------|-------------|------|-----|-----|",
    ]
    for row in result.traceability:
        jira_str = (
            " ".join(f"{t.key} {'✓' if t.status == 'Done' else '⚠'}" for t in row.jira_tickets)
            or "—"
        )
        pr_str = f"[#{row.pr_number}]({row.pr_url})" if row.pr_number else "—"
        breaking_marker = " ⚡BREAKING" if row.is_breaking else ""
        lines.append(
            f"| `{row.short_hash}` | "
            f"{row.description}{breaking_marker} | "
            f"{jira_str} | "
            f"{pr_str} | "
            f"{_ci_emoji(row.ci_status)} |"
        )
    return "\n".join(lines)


def _build_readiness_blocks(result: ReleaseResult) -> list[dict]:
    rec = result.readiness.recommendation
    badge = {"READY": "✅ READY", "HOLD": "⚠️ HOLD", "BLOCKED": "🚫 BLOCKED"}.get(rec, rec)
    risk_text = "\n".join(f"• {r}" for r in result.readiness.risk_factors) or "None identified"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Release Readiness: {badge}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Score:* {result.readiness.score}/100"},
                {"type": "mrkdwn", "text": f"*Bump:* {result.suggested_bump}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Rationale:*\n{result.readiness.rationale}",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Risk Factors:*\n{risk_text}"},
        },
    ]
    if result.readiness.rollback_plan:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Rollback Plan:*\n{result.readiness.rollback_plan}",
                },
            }
        )
    return blocks


_SLACK_TEXT_LIMIT = 2900  # Slack hard limit is 3000; leave headroom


def _safe_text(text: str | None, fallback: str = "_(no content)_") -> str:
    t = text.strip() if text and text.strip() else fallback
    if len(t) > _SLACK_TEXT_LIMIT:
        t = t[: _SLACK_TEXT_LIMIT - 30] + "\n\n_(truncated — see web for full notes)_"
    return t


def _section_blocks(text: str) -> list[dict]:
    """Split long text into multiple mrkdwn section blocks, each within the Slack limit."""
    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= _SLACK_TEXT_LIMIT:
            chunks.append(remaining)
            break
        # Split at a newline boundary near the limit
        split_at = remaining.rfind("\n", 0, _SLACK_TEXT_LIMIT)
        if split_at <= 0:
            split_at = _SLACK_TEXT_LIMIT
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    return [{"type": "section", "text": {"type": "mrkdwn", "text": c}} for c in chunks if c]


def post_all(
    result: ReleaseResult,
    channel: str,
    slack_token: str | None = None,
    thread_ts: str | None = None,
) -> None:
    """
    Post all 4 Slack messages for a release as thread replies.

    Errors are logged but not raised.
    """
    token = slack_token or os.environ.get("SLACK_BOT_TOKEN")
    if not token or not _SLACK_AVAILABLE:
        print(
            "[slack_poster] Skipping Slack post — "
            f"token={'set' if token else 'missing'}, "
            f"sdk={_SLACK_AVAILABLE}"
        )
        return

    client = WebClient(token=token)

    def _post(text, blocks, reply_ts=None):
        kwargs = dict(channel=channel, text=text, blocks=blocks)
        if reply_ts:
            kwargs["thread_ts"] = reply_ts
        return client.chat_postMessage(**kwargs)

    parent_ts = thread_ts  # all messages go into the existing thread

    try:
        # Message 1: Internal Announcement (reply to the ⏳ ack)
        resp = _post(
            text=f"📢 Release {result.version} — Internal Announcement",
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📢 Release {result.version} — Internal Announcement",
                    },
                },
                *_section_blocks(_safe_text(result.internal_announcement)),
            ],
            reply_ts=parent_ts,
        )
        if not parent_ts:
            parent_ts = resp["ts"]  # fallback: use this message as thread root
    except Exception as e:
        print(f"[slack_poster] Failed to post internal announcement: {e}")
        return

    try:
        # Message 2: Customer Release Notes
        _post(
            text=f"📋 {result.version} Customer Release Notes",
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📋 {result.version} — Customer Release Notes",
                    },
                },
                *_section_blocks(_safe_text(result.customer_notes)),
            ],
            reply_ts=parent_ts,
        )
    except Exception as e:
        print(f"[slack_poster] Failed to post customer notes: {e}")

    try:
        # Message 3: Marketing Release Notes (skip if None)
        if result.marketing_notes:
            _post(
                text=f"📣 {result.version} Marketing Release Notes",
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📣 {result.version} — Marketing Release Notes",
                        },
                    },
                    *_section_blocks(_safe_text(result.marketing_notes)),
                ],
                reply_ts=parent_ts,
            )
    except Exception as e:
        print(f"[slack_poster] Failed to post marketing notes: {e}")

    try:
        # Message 4: Internal Release Plan
        table = _build_traceability_table(result)
        readiness_blocks = _build_readiness_blocks(result)
        _post(
            text=f"🔍 Internal Release Plan — {result.version}",
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔍 Internal Release Plan — {result.version}",
                    },
                },
                *readiness_blocks,
                {"type": "divider"},
                *_section_blocks("*Traceability Matrix:*\n" + table),
            ],
            reply_ts=parent_ts,
        )
    except Exception as e:
        print(f"[slack_poster] Failed to post internal release plan: {e}")
