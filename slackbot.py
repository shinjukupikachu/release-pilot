#!/usr/bin/env python3
"""Release Pilot Slackbot — /release slash command router via Socket Mode."""

from __future__ import annotations

import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import httpx
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
SERVICE_URL = os.environ.get("SERVICE_URL", "http://localhost:30080/graphql")
SERVICE_BASE_URL = SERVICE_URL.rsplit("/graphql", 1)[0]

if not SLACK_BOT_TOKEN:
    print("ERROR: SLACK_BOT_TOKEN not set. Copy .env.example to .env and fill in your tokens.")
    sys.exit(1)
if not SLACK_APP_TOKEN:
    print("ERROR: SLACK_APP_TOKEN not set. Copy .env.example to .env and fill in your tokens.")
    sys.exit(1)

app = App(token=SLACK_BOT_TOKEN)

# Tracks pending interactive create sessions: (channel_id, thread_ts) → user_id
_pending_creates: dict[tuple[str, str], str] = {}

TRIGGER_RELEASE = """
mutation TriggerRelease($input: ReleaseInputGQL!) {
  triggerRelease(input: $input) {
    jobId
    status
  }
}
"""

# ── Help ──────────────────────────────────────────────────────────────────────

_HELP_TEXT = """\
*Release Pilot* — AI-assisted release automation

*Commands:*

`/release help`
  Show this help message.

`/release list`
  List all releases stored in the database (version, date, status, readiness score).

`/release create [version]`
  Start a release note generation workflow.
  • If *version* is provided (e.g. `v2.4.0`), generation begins immediately.
  • If omitted, a thread opens and you'll be prompted to enter the version.

`/release check [version]`
  Run a release readiness check.
  • Groups all commits since the last release by author and manager.
  • Looks up linked Jira tickets and reports their status (Done / open).
  • Lists the managers who need to sign off before shipping.
  • Optionally filter by a specific *version* already in the database.

`/release v2.3.0`
  Legacy shorthand — equivalent to `/release create v2.3.0`.
"""


def cmd_help(client, channel: str, user: str) -> None:
    resp = client.chat_postMessage(
        channel=channel,
        text=f"📖 Release Pilot command reference (requested by <@{user}>)",
    )
    client.chat_postMessage(
        channel=channel,
        thread_ts=resp["ts"],
        text=_HELP_TEXT,
        mrkdwn=True,
    )


# ── List ─────────────────────────────────────────────────────────────────────

_LIST_RELEASES = """
query ListReleases {
  releaseHistory(limit: 30) {
    version
    createdAt
    recommendation
    readinessScore
    suggestedBump
  }
}
"""


def cmd_list(client, channel: str, user: str, logger) -> None:
    resp = client.chat_postMessage(
        channel=channel,
        text=f"📋 Fetching release history... (requested by <@{user}>)",
    )
    thread_ts = resp["ts"]

    try:
        gql_resp = httpx.post(
            SERVICE_URL,
            json={"query": _LIST_RELEASES},
            timeout=10.0,
        )
        gql_resp.raise_for_status()
        data = gql_resp.json()
        if "errors" in data:
            raise ValueError(data["errors"])
        releases = data["data"]["releaseHistory"]
    except httpx.ConnectError:
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Could not reach release service at `{SERVICE_URL}`. Is it running?",
        )
        return
    except Exception as e:
        logger.error(f"list releases failed: {e}")
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Failed to fetch releases: {e}",
        )
        return

    if not releases:
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="No releases found in the database yet.",
        )
        return

    badge = {"READY": "🟢", "HOLD": "🟡", "BLOCKED": "🔴"}
    lines = ["*All Releases*\n"]
    for r in releases:
        icon = badge.get(r["recommendation"], "⚪")
        lines.append(
            f"{icon} *{r['version']}*  —  {r['createdAt'][:10]}  —  "
            f"score `{r['readinessScore']}/100`  —  bump `{r['suggestedBump']}`"
        )
    lines.append(f"\n_{len(releases)} release(s) total_")

    client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text="\n".join(lines),
        mrkdwn=True,
    )


# ── Create ────────────────────────────────────────────────────────────────────


def cmd_create(client, channel: str, user: str, version_arg: str, logger) -> None:
    if version_arg:
        _trigger_release(client, channel, user, version_arg, logger)
        return

    # No version given — open an interactive thread
    resp = client.chat_postMessage(
        channel=channel,
        text=(
            f"📝 <@{user}> Starting release note creation.\n\n"
            "What version would you like to release? (e.g. `v2.4.0`)\n"
            "_Reply in this thread with the version string._"
        ),
        mrkdwn=True,
    )
    thread_ts = resp["ts"]
    _pending_creates[(channel, thread_ts)] = user
    logger.info(f"Opened create session for {user} in thread {thread_ts}")


@app.event("message")
def handle_thread_reply(event, client, logger):
    """Pick up version replies in pending create threads."""
    thread_ts = event.get("thread_ts")
    channel = event.get("channel")
    user = event.get("user")
    text = (event.get("text") or "").strip()

    if not thread_ts or not channel or not text:
        return
    if event.get("bot_id"):
        return  # ignore our own messages

    key = (channel, thread_ts)
    pending_user = _pending_creates.get(key)
    if not pending_user:
        return

    # Only the original requester can respond
    if user != pending_user:
        return

    version = text.split()[0] if text else ""
    if not version.startswith("v"):
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"⚠️ `{version}` doesn't look like a version string — please use format `v2.4.0`.",
        )
        return

    del _pending_creates[key]
    client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f"Got it — generating release notes for *{version}*...",
        mrkdwn=True,
    )
    _trigger_release(client, channel, user, version, logger, thread_ts=thread_ts)


# ── Check ─────────────────────────────────────────────────────────────────────


def cmd_check(client, channel: str, user: str, version_arg: str, logger) -> None:
    from release_pilot.check import run_check

    version = version_arg or None
    label = f"*{version}*" if version else "latest test data"
    ack_resp = client.chat_postMessage(
        channel=channel,
        text=f"🔍 Running release readiness check on {label}... (requested by <@{user}>)",
        mrkdwn=True,
    )
    thread_ts = ack_resp["ts"]

    try:
        result = run_check(version)
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Readiness check failed: {e}",
        )
        return

    _post_check_result(client, channel, thread_ts, result)


def _post_check_result(client, channel: str, thread_ts: str, result) -> None:
    from release_pilot.check import ReadinessCheckResult

    r: ReadinessCheckResult = result
    overall = "🟢 *READY TO SHIP*" if r.is_ready else "🟡 *HOLD — open Jira tickets remain*"
    version_line = (
        f"*Version:* {r.version}" if r.version else "*Source:* test data (latest commits)"
    )
    from_line = f"  *Since:* {r.from_ref}" if r.from_ref else ""

    header = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 *Release Readiness Check*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{version_line}{chr(10) + from_line if from_line else ''}\n"
        f"*Commits:* {r.total_commits}   "
        f"*Jira tickets:* {len(r.all_jira)} "
        f"({r.closed_count} ✅ closed / {r.open_count} ⚠️ open)\n\n"
        f"{overall}"
    )
    client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=header, mrkdwn=True)

    # One message per author group
    for grp in r.author_groups:
        lines = [
            f"👤 *{grp.author}* — _{grp.title}_",
            f"   Manager: *{grp.manager_name}*",
            f"   Commits: {len(grp.commits)}",
        ]

        if grp.jira_tickets:
            lines.append("   Jira tickets:")
            for ticket in grp.jira_tickets:
                icon = "✅" if ticket.status.lower() in ("done", "closed", "resolved") else "⚠️"
                type_tag = f"[{ticket.issue_type}] " if ticket.issue_type else ""
                lines.append(
                    f"   {icon} `{ticket.key}` {type_tag}*{ticket.summary}* — _{ticket.status}_"
                )
        else:
            lines.append("   _(no linked Jira tickets)_")

        lines.append("")
        lines.append("   *Commits:*")
        for ci in grp.commits[:6]:  # cap to keep message short
            jira_tag = f" ({', '.join(ci.jira_keys)})" if ci.jira_keys else ""
            lines.append(f"   • `{ci.short_hash}` {ci.subject[:70]}{jira_tag}")
        if len(grp.commits) > 6:
            lines.append(f"   • _...and {len(grp.commits) - 6} more_")

        client.chat_postMessage(
            channel=channel, thread_ts=thread_ts, text="\n".join(lines), mrkdwn=True
        )

    # Sign-off summary
    sign_off_lines = ["*✍️ Sign-off Required From:*"]
    for mgr_name in r.sign_off_managers:
        from release_pilot import org as orgchart

        mgr = orgchart.lookup(mgr_name)
        handle = f" (@{mgr.slack_handle})" if mgr and mgr.slack_handle else ""
        sign_off_lines.append(f"  • {mgr_name}{handle}")

    if r.open_count > 0:
        open_keys = [
            t.key for t in r.all_jira if t.status.lower() not in ("done", "closed", "resolved")
        ]
        sign_off_lines.append(
            f"\n⚠️ *{r.open_count} open ticket(s) blocking release:* "
            f"{', '.join(f'`{k}`' for k in open_keys)}"
        )

    client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text="\n".join(sign_off_lines),
        mrkdwn=True,
    )


# ── Release trigger (existing pipeline) ───────────────────────────────────────


def _trigger_release(
    client, channel: str, user: str, version: str, logger, thread_ts: str | None = None
) -> None:
    if not version.startswith("v"):
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"⚠️ Invalid version `{version}` — must start with `v` (e.g. `v2.3.0`).",
        )
        return

    ack_resp = client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f"⏳ Generating release notes for *{version}*... (triggered by <@{user}>)",
        mrkdwn=True,
    )
    reply_thread_ts = ack_resp["ts"]

    try:
        resp = httpx.post(
            SERVICE_URL,
            json={
                "query": TRIGGER_RELEASE,
                "variables": {
                    "input": {
                        "version": version,
                        "fromRef": "auto",
                        "channel": channel,
                        "threadTs": reply_thread_ts,
                    }
                },
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            raise ValueError(f"GraphQL errors: {data['errors']}")

        job_id = data["data"]["triggerRelease"]["jobId"]
        logger.info(f"Release job started: {job_id} for {version}")

    except httpx.ConnectError:
        client.chat_postMessage(
            channel=channel,
            thread_ts=reply_thread_ts,
            text=f"❌ Could not reach release service at `{SERVICE_URL}`. Is it running?",
        )
    except Exception as e:
        logger.error(f"Failed to trigger release {version}: {e}")
        client.chat_postMessage(
            channel=channel,
            thread_ts=reply_thread_ts,
            text=f"❌ Failed to trigger release `{version}`: {e}",
        )


# ── PDF button action handlers ────────────────────────────────────────────────


@app.action("generate_pdf")
def handle_generate_pdf(ack, body, client, logger):
    ack()
    import json as _json

    payload = _json.loads(body["actions"][0]["value"])
    version = payload["version"]
    channel = payload["channel"]
    msg_ts = body["message"]["ts"]

    # Update button message to "Generating..."
    client.chat_update(
        channel=channel,
        ts=msg_ts,
        text=f"⏳ Generating PDF for *{version}*...",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⏳ Generating PDF for *{version}*...",
                },
            },
        ],
    )

    try:
        resp = httpx.post(
            f"{SERVICE_BASE_URL}/releases/{version}/generate-pdf",
            timeout=30.0,
        )
        resp.raise_for_status()
        pdf_url = resp.json()["url"]
        web_url = f"{SERVICE_BASE_URL}/releases/{version}"

        # Update button message to success
        client.chat_update(
            channel=channel,
            ts=msg_ts,
            text=f"📄 PDF ready for {version}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📄 *{version}* release notes PDF is ready!",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "📄 Download PDF"},
                            "url": pdf_url,
                            "action_id": "open_pdf",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🌐 View on Web"},
                            "url": web_url,
                            "action_id": "open_web",
                        },
                    ],
                },
            ],
        )
    except Exception as e:
        logger.error(f"PDF generation failed for {version}: {e}")
        client.chat_update(
            channel=channel,
            ts=msg_ts,
            text=f"❌ PDF generation failed for `{version}`: {e}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ PDF generation failed: `{e}`",
                    },
                },
            ],
        )


@app.action("skip_pdf")
def handle_skip_pdf(ack, body, client):
    ack()
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="PDF generation skipped.",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📄 PDF skipped — you can always view the release on the web server.",
                },
            },
        ],
    )


@app.action("open_pdf")
def handle_open_pdf(ack):
    ack()


@app.action("open_web")
def handle_open_web(ack):
    ack()


# ── Main command handler ───────────────────────────────────────────────────────


@app.command("/release")
def handle_release(ack, command, client, logger):
    ack()

    raw = (command.get("text") or "").strip()
    parts = raw.split(None, 1)
    subcommand = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""
    channel = command.get("channel_id", "")
    user = command.get("user_id", "")

    if subcommand in ("", "help"):
        cmd_help(client, channel, user)
    elif subcommand == "list":
        cmd_list(client, channel, user, logger)
    elif subcommand == "create":
        cmd_create(client, channel, user, arg, logger)
    elif subcommand == "check":
        cmd_check(client, channel, user, arg, logger)
    else:
        # Treat the whole text as a version (backward-compat: `/release v2.3.0`)
        cmd_create(client, channel, user, raw, logger)


if __name__ == "__main__":
    print("⚡ Release Pilot Slackbot connecting via Socket Mode...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
