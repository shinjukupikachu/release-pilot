from __future__ import annotations

from pathlib import Path

from release_pilot.agents.base import AgentDefinition


def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()


_OUTPUT_CONTRACT = """

## Your task

You receive a structured list of commits with CI results, Jira ticket statuses, and 
breaking change information.

Apply the Release Manager scoring rules (start at 100, apply deductions). Apply 
QA Manager regression risk assessment per commit.

Return ONE JSON object only — no prose, no markdown fences:
{
  "score": 85,
  "recommendation": "READY",
  "rationale": (
      "All CI checks pass on customer-facing commits. One internal chore commit "
      "has no CI evidence but poses low risk."
  ),
  "risk_factors": [
      (
          "Breaking API change on PR #46 has 2 failing CI checks "
          "(integration/api-backward-compat, integration/client-sdk-v1)"
      )
  ],
  "rollback_plan": "Revert to v2.2.0 tag. No database migrations in this release.",
  "per_commit_risk": [
    {
      "short_hash": "b2c3d4e",
      "risk_level": "critical",
      "reason": "Breaking API rename with 2 failing backward-compat CI checks",
      "mitigation": (
          "integration/api-backward-compat and "
          "integration/client-sdk-v1 tests must pass before release"
      )
    }
  ]
}

Recommendation thresholds:
- READY: score >= 80 AND no failing CI on customer-facing commits
- HOLD: score 60-79 OR failing CI on internal-only commits
- BLOCKED: score < 60 OR any failing CI on customer-facing/breaking commits
"""

READINESS_AGENT = AgentDefinition(
    description="Release readiness scoring — Release Manager + QA Manager personas",
    prompt=_load_runbook("release-manager") + "\n\n" + _load_runbook("qa-manager") + _OUTPUT_CONTRACT,
    tools=[],
    model="sonnet",
)
