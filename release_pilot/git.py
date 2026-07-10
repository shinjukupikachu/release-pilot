from __future__ import annotations
import json
import subprocess
from release_pilot.models import CommitInfo
from release_pilot import config


def get_commits(from_ref: str = "HEAD~10", to_ref: str = "HEAD") -> list[CommitInfo]:
    """Return commits between from_ref and to_ref.
    When TEST_DATA=1, loads from test_data/commits.json instead of running git.
    """
    if config.TEST_DATA:
        data = json.loads((config.TEST_DATA_DIR / "commits.json").read_text())
        return [CommitInfo(**c) for c in data]

    # git log with separator to handle multi-line bodies
    SEP = "---COMMIT---"
    fmt = f"%H%n%h%n%an%n%aI%n%s%n%b{SEP}"
    result = subprocess.run(
        ["git", "log", f"{from_ref}..{to_ref}", f"--format={fmt}"],
        capture_output=True,
        text=True,
        check=True,
    )
    commits = []
    for block in result.stdout.split(SEP):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n", 5)
        if len(lines) < 5:
            continue
        hash_, short_hash, author, date, subject = lines[:5]
        body = lines[5].strip() if len(lines) > 5 else ""
        commits.append(
            CommitInfo(
                hash=hash_.strip(),
                short_hash=short_hash.strip(),
                author=author.strip(),
                date=date.strip(),
                subject=subject.strip(),
                body=body,
            )
        )
    return commits
