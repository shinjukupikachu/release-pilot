from __future__ import annotations

from release_pilot.store import (
    get_release,
    init_db,
    list_releases,
    release_exists,
    save_release,
)


class TestInitDb:
    def test_creates_tables(self, tmp_db):
        import sqlite3

        init_db(tmp_db)
        with sqlite3.connect(tmp_db) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "releases" in tables
        assert "traceability_rows" in tables

    def test_idempotent(self, tmp_db):
        init_db(tmp_db)
        init_db(tmp_db)  # should not raise


class TestSaveAndGetRelease:
    def test_round_trip(self, sample_release_result, tmp_db):
        init_db(tmp_db)
        rid = save_release(sample_release_result, "v2.2.0", db_path=tmp_db)
        assert isinstance(rid, int)
        loaded = get_release("v2.3.0", db_path=tmp_db)
        assert loaded is not None
        assert loaded.version == "v2.3.0"
        assert loaded.suggested_bump == "major"
        assert loaded.readiness.score == 82
        assert loaded.readiness.recommendation == "READY"

    def test_get_nonexistent_returns_none(self, tmp_db):
        init_db(tmp_db)
        assert get_release("v99.99.99", db_path=tmp_db) is None

    def test_marketing_notes_nullable(self, tmp_db):
        from release_pilot.models import ReadinessReport, ReleaseResult

        init_db(tmp_db)
        r = ReleaseResult(
            version="v1.0.0",
            suggested_bump="minor",
            readiness=ReadinessReport(
                score=90,
                recommendation="READY",
                rationale="ok",
                risk_factors=[],
                rollback_plan="",
            ),
            internal_announcement="hello",
            customer_notes="world",
            marketing_notes=None,
            traceability=[],
        )
        save_release(r, "v0.9.0", db_path=tmp_db)
        loaded = get_release("v1.0.0", db_path=tmp_db)
        assert loaded.marketing_notes is None


class TestListReleases:
    def test_returns_newest_first(self, sample_release_result, tmp_db):
        from release_pilot.models import ReadinessReport, ReleaseResult

        init_db(tmp_db)
        save_release(sample_release_result, "v2.2.0", db_path=tmp_db)
        r2 = ReleaseResult(
            version="v2.4.0",
            suggested_bump="minor",
            readiness=ReadinessReport(
                score=95,
                recommendation="READY",
                rationale="ok",
                risk_factors=[],
                rollback_plan="",
            ),
            internal_announcement="v2.4.0 released",
            customer_notes="What's new in v2.4.0",
            traceability=[],
        )
        save_release(r2, "v2.3.0", db_path=tmp_db)
        releases = list_releases(db_path=tmp_db)
        assert releases[0].version == "v2.4.0"
        assert releases[1].version == "v2.3.0"

    def test_limit_respected(self, tmp_db):
        from release_pilot.models import ReadinessReport, ReleaseResult

        init_db(tmp_db)
        for i in range(5):
            r = ReleaseResult(
                version=f"v1.0.{i}",
                suggested_bump="patch",
                readiness=ReadinessReport(
                    score=80,
                    recommendation="READY",
                    rationale="ok",
                    risk_factors=[],
                    rollback_plan="",
                ),
                internal_announcement=f"v1.0.{i}",
                customer_notes=f"v1.0.{i}",
                traceability=[],
            )
            save_release(r, "v0.0.0", db_path=tmp_db)
        limited = list_releases(db_path=tmp_db, limit=3)
        assert len(limited) == 3


class TestReleaseExists:
    def test_returns_true_after_save(self, sample_release_result, tmp_db):
        init_db(tmp_db)
        save_release(sample_release_result, "v2.2.0", db_path=tmp_db)
        assert release_exists("v2.3.0", db_path=tmp_db) is True

    def test_returns_false_before_save(self, tmp_db):
        init_db(tmp_db)
        assert release_exists("v99.0.0", db_path=tmp_db) is False
