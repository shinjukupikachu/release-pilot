from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentDefinition:
    description: str
    prompt: str
    tools: list[str] = field(default_factory=list)
    model: str = "claude-sonnet-4-6"
