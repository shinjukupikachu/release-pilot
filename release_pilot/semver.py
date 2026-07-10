from __future__ import annotations
from release_pilot.models import ParsedCommit, ChangeSet

_MINOR_TYPES = {"feat"}
_PATCH_TYPES = {"fix", "perf"}


def calculate_bump(commits: list[ParsedCommit]) -> str:
    """Returns 'major', 'minor', 'patch', or 'none'."""
    if any(c.is_breaking for c in commits):
        return "major"
    if any(c.commit_type in _MINOR_TYPES for c in commits):
        return "minor"
    if any(c.commit_type in _PATCH_TYPES for c in commits):
        return "patch"
    return "none"


def build_changeset(
    version: str, from_ref: str, commits: list[ParsedCommit]
) -> ChangeSet:
    return ChangeSet(
        version=version,
        from_ref=from_ref,
        commits=commits,
        breaking=[c for c in commits if c.is_breaking],
        suggested_bump=calculate_bump(commits),
    )
