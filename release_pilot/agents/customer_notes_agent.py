from __future__ import annotations

from pathlib import Path

from release_pilot.agents.base import AgentDefinition


def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()


_OUTPUT_CONTRACT = """

## Your task

You receive a list of commits classified as "customer" or "marketing" tier. Write Customer Release Notes.

Voice: clear, benefit-focused, low-jargon. For breaking changes, include "What you need to do" migration guidance.

Return ONE JSON object only — no prose, no markdown fences:
{
  "customer_notes": "## NyankoOS v2.3.0 — What's New\\n\\n..."
}

Format customer_notes as clean markdown. Use ## for version header, ### for categories (New Features, Bug Fixes, Performance, Important: Breaking Changes).

Rules:
- Do NOT include Jira ticket numbers (no NYANKO-XXX references)
- Do NOT include PR numbers or links
- Do NOT include CI status or internal metrics
- Focus on customer benefit and outcome, not implementation detail
- For breaking changes include a clear "What you need to do:" action item
- Write as if publishing to a public changelog
"""

CUSTOMER_NOTES_AGENT = AgentDefinition(
    description="Write customer-facing release notes",
    prompt=_load_runbook("product-manager") + _OUTPUT_CONTRACT,
    tools=[],
    model="sonnet",
)
