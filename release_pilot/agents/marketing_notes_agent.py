from __future__ import annotations
from pathlib import Path
from release_pilot.agents.base import AgentDefinition


def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()


_OUTPUT_CONTRACT = """

## Your task

You receive a list of commits classified as "marketing" tier. Write Marketing Release Notes for prospects, partners, and industry audiences.

Voice: outcome-first, aspirational but grounded. Lead with business value. No engineering jargon.

If no commits qualify for marketing-tier announcement, return null for marketing_notes.

Return ONE JSON object only — no prose, no markdown fences:
{
  "marketing_notes": "## NyankoOS v2.3.0 Delivers..."
}

OR if nothing is marketing-worthy:
{
  "marketing_notes": null
}
"""

MARKETING_NOTES_AGENT = AgentDefinition(
    description="Write marketing-facing release notes",
    prompt=_load_runbook("product-manager") + _OUTPUT_CONTRACT,
    tools=[],
    model="sonnet",
)
