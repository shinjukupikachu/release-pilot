from __future__ import annotations

from release_pilot.parser import parse_commits
from release_pilot.semver import build_changeset, calculate_bump


class TestCalculateBump:
    def test_breaking_returns_major(self, sample_commit_infos):
        parsed = parse_commits(sample_commit_infos)
        # sample_commit_infos[1] is breaking
        assert calculate_bump(parsed) == "major"

    def test_feat_only_returns_minor(self):
        from release_pilot.models import ParsedCommit

        commits = [
            ParsedCommit(
                hash="a" * 40,
                short_hash="aaaaaaa",
                author="A",
                date="2026-06-01T00:00:00Z",
                subject="feat: foo",
                body="",
                commit_type="feat",
                scope=None,
                is_breaking=False,
                breaking_note=None,
                clean_subject="foo",
            )
        ]
        assert calculate_bump(commits) == "minor"

    def test_fix_only_returns_patch(self):
        from release_pilot.models import ParsedCommit

        commits = [
            ParsedCommit(
                hash="b" * 40,
                short_hash="bbbbbbb",
                author="B",
                date="2026-06-01T00:00:00Z",
                subject="fix: bar",
                body="",
                commit_type="fix",
                scope=None,
                is_breaking=False,
                breaking_note=None,
                clean_subject="bar",
            )
        ]
        assert calculate_bump(commits) == "patch"

    def test_chore_only_returns_none(self):
        from release_pilot.models import ParsedCommit

        commits = [
            ParsedCommit(
                hash="c" * 40,
                short_hash="ccccccc",
                author="C",
                date="2026-06-01T00:00:00Z",
                subject="chore: update deps",
                body="",
                commit_type="chore",
                scope=None,
                is_breaking=False,
                breaking_note=None,
                clean_subject="update deps",
            )
        ]
        assert calculate_bump(commits) == "none"

    def test_perf_returns_patch(self):
        from release_pilot.models import ParsedCommit

        commits = [
            ParsedCommit(
                hash="d" * 40,
                short_hash="ddddddd",
                author="D",
                date="2026-06-01T00:00:00Z",
                subject="perf: speed",
                body="",
                commit_type="perf",
                scope=None,
                is_breaking=False,
                breaking_note=None,
                clean_subject="speed",
            )
        ]
        assert calculate_bump(commits) == "patch"


class TestBuildChangeset:
    def test_sets_breaking_list(self, sample_commit_infos):
        parsed = parse_commits(sample_commit_infos)
        cs = build_changeset("v2.3.0", "v2.2.0", parsed)
        assert cs.version == "v2.3.0"
        assert cs.from_ref == "v2.2.0"
        breaking_hashes = {c.short_hash for c in cs.breaking}
        assert "b2c3d4e" in breaking_hashes

    def test_no_breaking_commits(self):
        from release_pilot.models import ParsedCommit

        commits = [
            ParsedCommit(
                hash="e" * 40,
                short_hash="eeeeeee",
                author="E",
                date="2026-06-01T00:00:00Z",
                subject="fix: baz",
                body="",
                commit_type="fix",
                scope=None,
                is_breaking=False,
                breaking_note=None,
                clean_subject="baz",
            )
        ]
        cs = build_changeset("v1.0.1", "v1.0.0", commits)
        assert cs.breaking == []
        assert cs.suggested_bump == "patch"
