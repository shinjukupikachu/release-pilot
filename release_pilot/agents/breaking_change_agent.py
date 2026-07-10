from __future__ import annotations

from pathlib import Path

from release_pilot.agents.base import AgentDefinition


def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()


_OUTPUT_CONTRACT = """

## Your task

You receive one or more breaking commits. Analyze the breaking changes and produce a structured summary for the internal release plan.

Return ONE JSON object only — no prose, no markdown fences:
{
  "affected_components": ["API /api/v1/robot-status", "Client SDK v1"],
  "severity": "HIGH",
  "migration_steps": [
    "Update all API clients from /api/v1/robot-status to /api/v2/status",
    "Upgrade client SDK to v2.x before deploying"
  ],
  "customer_action_required": true
}
"""

BREAKING_CHANGE_AGENT = AgentDefinition(
    description="Analyze breaking changes and produce migration guidance",
    prompt=_load_runbook("release-manager") + _OUTPUT_CONTRACT,
    tools=[],
    model="sonnet",
)
