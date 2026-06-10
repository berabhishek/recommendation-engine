from __future__ import annotations

import gzip
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.database import recreate_schema
from app.importer import import_imdb_data
from app.migrations import get_current_database_revision, get_head_revision, upgrade_database


def write_gz(path: Path, lines: list[str]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


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


def test_upgrade_database_stamps_recreate_schema_legacy_baseline_only(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    # Simulate a pre-Alembic database that exactly matches the current metadata.
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


def test_real_importer_works_on_alembic_created_schema(tmp_path):
    db_path = tmp_path / "import.db"
    data_dir = tmp_path / "imdb"
    data_dir.mkdir(parents=True, exist_ok=True)

    write_gz(
        data_dir / "title.basics.tsv.gz",
        [
            "tconst\ttitleType\tprimaryTitle\toriginalTitle\tisAdult\tstartYear\tendYear\truntimeMinutes\tgenres",
            "tt0000001\tmovie\tExample Movie\tExample Movie\t0\t2024\t\\N\t120\tDrama",
            "tt0000002\ttvEpisode\tExample Episode\tExample Episode\t0\t2024\t\\N\t45\tDrama,Short",
        ],
    )
    write_gz(
        data_dir / "name.basics.tsv.gz",
        [
            "nconst\tprimaryName\tbirthYear\tdeathYear\tprimaryProfession\tknownForTitles",
            "nm0000001\tExample Person\t1980\t\\N\tactor,director\ttt0000001,tt0000002",
        ],
    )
    write_gz(
        data_dir / "title.ratings.tsv.gz",
        [
            "tconst\taverageRating\tnumVotes",
            "tt0000001\t8.5\t1000",
            "tt0000002\t7.2\t150",
        ],
    )
    write_gz(
        data_dir / "title.principals.tsv.gz",
        [
            "tconst\tordering\tnconst\tcategory\tjob\tcharacters",
            "tt0000001\t1\tnm0000001\tactor\t\\N\t[\"Lead\"]",
        ],
    )
    write_gz(
        data_dir / "title.akas.tsv.gz",
        [
            "titleId\tordering\ttitle\tregion\tlanguage\ttypes\tattributes\tisOriginalTitle",
            "tt0000001\t1\tExample Movie\tUS\ten\t\\N\t\\N\t1",
        ],
    )
    write_gz(
        data_dir / "title.crew.tsv.gz",
        [
            "tconst\tdirectors\twriters",
            "tt0000001\tnm0000001\tnm0000001",
        ],
    )
    write_gz(
        data_dir / "title.episode.tsv.gz",
        [
            "tconst\tparentTconst\tseasonNumber\tepisodeNumber",
            "tt0000002\ttt0000001\t1\t1",
        ],
    )

    upgrade_database(f"sqlite:///{db_path}")
    row_count = import_imdb_data(
        f"sqlite:///{db_path}",
        data_dir,
        reset=False,
        prepare_schema=False,
    )

    assert row_count == 12

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM movies")).scalar_one() == 2
            assert conn.execute(text("SELECT COUNT(*) FROM people")).scalar_one() == 1
            assert conn.execute(text("SELECT COUNT(*) FROM movie_ratings")).scalar_one() == 2
            assert conn.execute(text("SELECT COUNT(*) FROM movie_genres")).scalar_one() == 3
            assert conn.execute(text("SELECT COUNT(*) FROM movie_principals")).scalar_one() == 1
            assert conn.execute(text("SELECT COUNT(*) FROM movie_crew_links")).scalar_one() == 2
            assert conn.execute(text("SELECT COUNT(*) FROM movie_episodes")).scalar_one() == 1
            assert conn.execute(text("SELECT COUNT(*) FROM movie_akas")).scalar_one() == 1
            assert conn.execute(text("SELECT COUNT(*) FROM person_professions")).scalar_one() == 2
            assert conn.execute(text("SELECT COUNT(*) FROM person_known_for_titles")).scalar_one() == 2
    finally:
        engine.dispose()
