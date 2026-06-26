# Runbooks — Agent Persona Definitions

Runbooks define how each agent persona reasons about its task. Each agent loads its runbook as the first section of its system prompt, before the output contract. This makes agent behavior transparent, auditable, and tunable without code changes.

## How Agents Load Runbooks

```python
from pathlib import Path

def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()

READINESS_AGENT = AgentDefinition(
    description="Release readiness scoring — Release Manager persona",
    prompt=_load_runbook("release-manager") + "\n\n" + READINESS_OUTPUT_CONTRACT,
    tools=[],
    model="sonnet",
)
```

## Runbook to Agent Mapping

| Runbook | Agent(s) |
|---|---|
| `release-manager.md` | `readiness_agent.py` |
| `qa-manager.md` | `readiness_agent.py` (appended after release-manager) |
| `product-manager.md` | `classifier_agent.py`, `customer_notes_agent.py`, `marketing_notes_agent.py` |
