from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.database import recreate_schema
from app.migrations import get_current_database_revision, get_head_revision, upgrade_database


def test_upgrade_database_creates_complete_schema_from_empty_db(tmp_path):
    db_path = tmp_path / "empty.db"

    revision = upgrade_database(f"sqlite:///{db_path}")

    assert revision == get_head_revision(f"sqlite:///{db_path}")
    assert get_current_database_revision(f"sqlite:///{db_path}") == revision

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "alembic_version",
            "app_state",
            "import_runs",
            "movie_akas",
            "movie_crew_links",
            "movie_episodes",
            "movie_genres",
            "movie_principals",
            "movie_ratings",
            "movies",
            "people",
            "person_known_for_titles",
            "person_professions",
        } <= tables
    finally:
        engine.dispose()


def test_upgrade_database_stamps_an_exact_legacy_schema(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    recreate_schema(engine, drop_existing=False)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO movies (id, title_type, primary_title, original_title, genres_text, is_adult) "
                "VALUES ('ttlegacy1', 'movie', 'Legacy Movie', 'Legacy Movie', 'Drama', 0)"
            )
        )

    engine.dispose()

    revision = upgrade_database(f"sqlite:///{db_path}")
    assert get_current_database_revision(f"sqlite:///{db_path}") == revision

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM movies WHERE id = 'ttlegacy1'")).scalar_one() == 1
    finally:
        engine.dispose()


def test_upgrade_database_rejects_partial_legacy_schema(tmp_path):
    db_path = tmp_path / "dirty.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE movies ("
                "id VARCHAR(20) PRIMARY KEY, "
                "title_type VARCHAR(50) NOT NULL, "
                "primary_title VARCHAR(512) NOT NULL, "
                "original_title VARCHAR(512) NOT NULL, "
                "is_adult BOOLEAN NOT NULL"
                ")"
            )
        )

    engine.dispose()

    try:
        upgrade_database(f"sqlite:///{db_path}")
    except RuntimeError as exc:
        assert "legacy baseline" in str(exc)
    else:
        raise AssertionError("expected upgrade_database to reject the partial schema")
