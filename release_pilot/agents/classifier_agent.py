from __future__ import annotations
from pathlib import Path
from release_pilot.agents.base import AgentDefinition


def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()


_OUTPUT_CONTRACT = """

## Your task

You receive a structured list of commits for this release. Each commit shows: short_hash, type, scope, whether it is breaking, subject, Jira tickets (key + status + type), PR number, and CI results.

Classify each commit with an audience tier:
- "internal" — chore, ci, build, docs, internal-only fixes, refactors
- "customer" — user-visible fixes, new features, performance improvements, breaking changes
- "marketing" — major new capabilities, enterprise integrations, significant performance milestones

Then write the Internal Announcement (all-staff Slack/email).

Return ONE JSON object only — no prose, no markdown fences:
{
  "commits": [
    {
      "short_hash": "a1b2c3d",
      "commit_type": "feat",
      "scope": "picking",
      "is_breaking": false,
      "audience": "customer",
      "reason": "New user-visible capability in picking module"
    }
  ],
  "internal_announcement": "## v2.3.0 shipped\n\n### ✨ Features\n- Vision-guided pick confirmation — 18% drop reduction ([#45](https://github.com/nyanko/nyankoos/pull/45)) `NYANKO-456`\n- SAP EWM integration connector ([#54](https://github.com/nyanko/nyankoos/pull/54)) `NYANKO-678`\n- Japanese UI locale ja-JP ([#66](https://github.com/nyanko/nyankoos/pull/66)) `NYANKO-888`\n\n### 🐛 Bug Fixes\n- Palletizing stack overflow on dense layers ([#47](https://github.com/nyanko/nyankoos/pull/47)) `NYANKO-234`\n- Token refresh race condition 401 loops ([#49](https://github.com/nyanko/nyankoos/pull/49)) `NYANKO-890`\n- Depth sensor calibration in low light ([#53](https://github.com/nyanko/nyankoos/pull/53)) `NYANKO-123`\n- Suction cup pressure loss at high speed ([#58](https://github.com/nyanko/nyankoos/pull/58)) `NYANKO-112`\n- TCP keepalive drops on 2.4GHz Wi-Fi ([#60](https://github.com/nyanko/nyankoos/pull/60)) `NYANKO-333`\n- Multi-arm handoff deadlock ([#63](https://github.com/nyanko/nyankoos/pull/63)) `NYANKO-666`\n- Duplicate telemetry heartbeats on reconnect ([#67](https://github.com/nyanko/nyankoos/pull/67)) `NYANKO-999`\n\n### ⚡ Performance\n- Motion planning latency 120ms → 72ms ([#48](https://github.com/nyanko/nyankoos/pull/48)) `NYANKO-567`\n- GPU bounding box inference 85ms → 22ms ([#61](https://github.com/nyanko/nyankoos/pull/61)) `NYANKO-444`\n\n### ⚠️ Breaking Changes — customer comms required before deploy\n- API rename `/api/v1/robot-status` → `/api/v2/status` ([#46](https://github.com/nyanko/nyankoos/pull/46)) `NYANKO-789`\n  - CI: ⚠️ 2 failures — `integration/api-backward-compat`, `integration/client-sdk-v1`\n- SDK: `RobotClient.connect_v1()` removed ([#62](https://github.com/nyanko/nyankoos/pull/62)) `NYANKO-555`\n\n### 🔒 Security\n- mTLS enforced on all inter-service connections ([#64](https://github.com/nyanko/nyankoos/pull/64)) `NYANKO-777`\n  - CI: ⚠️ 1 failure — `security/cert-provisioning-e2e` — cert provisioning must complete before rollout\n\nPing #releases with issues."
}

The internal_announcement is a detailed, factual engineering summary for the team. Structure it with sections: Features, Bug Fixes, Performance, Breaking Changes, Security. For EVERY commit include:
- A one-line description
- The PR link as ([#number](url)) using the pr_number and pr_url from the input
- The Jira key(s) as inline code `NYANKO-XXX`
- For any PR with CI failures, add an indented line: "  - CI: ⚠️ N failures — `check-name-1`, `check-name-2`"

Do NOT use marketing language. This is a peer-to-peer engineering handoff document.

Include ALL commits from the input in the output commits array.
"""

CLASSIFIER_AGENT = AgentDefinition(
    description="Classify commits by audience and write internal announcement",
    prompt=_load_runbook("product-manager") + _OUTPUT_CONTRACT,
    tools=[],
    model="sonnet",
)
