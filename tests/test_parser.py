from __future__ import annotations

from release_pilot.parser import parse_body, parse_commit, parse_commits, parse_subject


class TestParseSubject:
    def test_feat_with_scope(self):
        t, scope, breaking, clean = parse_subject("feat(picking): add vision confirmation")
        assert t == "feat"
        assert scope == "picking"
        assert breaking is False
        assert clean == "add vision confirmation"

    def test_fix_no_scope(self):
        t, scope, breaking, clean = parse_subject("fix: resolve stack overflow")
        assert t == "fix"
        assert scope is None
        assert breaking is False

    def test_breaking_bang(self):
        t, scope, breaking, clean = parse_subject("feat(api)!: rename endpoint")
        assert t == "feat"
        assert breaking is True

    def test_chore_type(self):
        t, scope, breaking, clean = parse_subject("chore(ci): upgrade runners")
        assert t == "chore"

    def test_missing_prefix_defaults_to_chore(self):
        t, scope, breaking, clean = parse_subject("no conventional prefix here")
        assert t == "chore"
        assert scope is None
        assert breaking is False
        assert clean == "no conventional prefix here"

    def test_docs_type(self):
        t, scope, breaking, clean = parse_subject("docs(api): update REST reference")
        assert t == "docs"


class TestParseBody:
    def test_extracts_jira_keys(self):
        note, keys = parse_body("Fixes bug.\n\nNYANKO-456")
        assert "NYANKO-456" in keys

    def test_extracts_breaking_note(self):
        note, keys = parse_body("BREAKING CHANGE: /api/v1 removed.\n\nNYANKO-789")
        assert note == "/api/v1 removed."
        assert "NYANKO-789" in keys

    def test_deduplicates_keys(self):
        _, keys = parse_body("NYANKO-456 is fixed. See NYANKO-456 for details.")
        assert keys.count("NYANKO-456") == 1

    def test_no_jira_keys(self):
        note, keys = parse_body("Simple fix, no ticket.")
        assert keys == []
        assert note is None


class TestParseCommit:
    def test_jira_key_dedup_across_subject_and_body(self, sample_commit_infos):
        # commit with NYANKO-456 in both subject and body
        commit = sample_commit_infos[0]  # subject has NYANKO-456, body has NYANKO-456
        parsed = parse_commit(commit)
        assert parsed.jira_keys.count("NYANKO-456") == 1

    def test_breaking_from_body(self, sample_commit_infos):
        commit = sample_commit_infos[1]  # has BREAKING CHANGE in body
        parsed = parse_commit(commit)
        assert parsed.is_breaking is True
        assert "NYANKO-789" in parsed.jira_keys

    def test_parse_commits_returns_all(self, sample_commit_infos):
        parsed = parse_commits(sample_commit_infos)
        assert len(parsed) == len(sample_commit_infos)
