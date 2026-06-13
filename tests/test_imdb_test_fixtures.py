from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from app.importer import import_imdb_data


def test_committed_imdb_test_fixtures_import_cleanly(tmp_path):
    db_path = tmp_path / "recommendation.db"
    data_dir = Path(__file__).resolve().parent / "fixtures" / "imdb-test"

    import_imdb_data(f"sqlite:///{db_path}", data_dir, reset=True, prepare_schema=True, rebuild_indexes=True)

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM movies")).scalar_one() == 4
        assert conn.execute(text("SELECT COUNT(*) FROM people")).scalar_one() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM movie_ratings")).scalar_one() == 2
        assert conn.execute(text("SELECT COUNT(*) FROM movie_principals")).scalar_one() == 2
        assert conn.execute(text("SELECT COUNT(*) FROM movie_crew_links")).scalar_one() == 4
        assert conn.execute(text("SELECT COUNT(*) FROM movie_akas")).scalar_one() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM movie_episodes")).scalar_one() == 1
        assert conn.execute(text("SELECT value FROM app_state WHERE key = 'bootstrap_complete'")).scalar_one_or_none() is None
