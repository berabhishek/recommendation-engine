from __future__ import annotations

import gzip
from pathlib import Path

from sqlalchemy import create_engine, text

from app.database import recreate_schema
import scripts.docker_entrypoint as docker_entrypoint
from scripts.download_imdb_data import IMDB_FILES


def write_gz(path: Path, lines: list[str]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def test_bootstrap_runs_download_then_import_and_records_state(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "recommendation.db"
    template_path = tmp_path / "template" / "recommendation.db"
    data_dir = tmp_path / "imdb"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    recreate_schema(create_engine(f"sqlite:///{template_path}"), drop_existing=False)

    calls: list[str] = []

    def fake_download(target_dir: Path, overwrite: bool = False) -> None:
        calls.append("download")
        assert target_dir == data_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "title.ratings.tsv.gz").write_bytes(b"data")

    def fake_import(database_url: str, import_data_dir: Path, **kwargs) -> None:
        calls.append("import")
        assert database_url == f"sqlite:///{db_path}"
        assert import_data_dir == data_dir
        assert kwargs["reset"] is False
        assert kwargs["prepare_schema"] is False
        assert kwargs["rebuild_indexes"] is True

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DB_TEMPLATE_PATH", str(template_path))
    monkeypatch.setattr(docker_entrypoint, "download_imdb_data", fake_download)
    monkeypatch.setattr(docker_entrypoint, "import_imdb_data", fake_import)

    docker_entrypoint.bootstrap_database()

    assert calls == ["download", "import"]
    with create_engine(f"sqlite:///{db_path}").connect() as conn:
        assert conn.execute(text("SELECT value FROM app_state WHERE key = 'bootstrap_complete'")).scalar_one() == "true"
    assert list(data_dir.glob("*.tsv.gz")) == []

    docker_entrypoint.bootstrap_database()
    assert calls == ["download", "import"]


def test_bootstrap_rebuilds_dirty_database_before_importing(tmp_path, monkeypatch):
    data_dir = tmp_path / "imdb"
    db_path = tmp_path / "data" / "recommendation.db"
    template_path = tmp_path / "template" / "recommendation.db"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    recreate_schema(create_engine(f"sqlite:///{template_path}"), drop_existing=False)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    dirty_engine = create_engine(f"sqlite:///{db_path}")
    recreate_schema(dirty_engine, drop_existing=False)
    with dirty_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO movies (id, title_type, primary_title, original_title, is_adult) "
                "VALUES ('ttdirty0001', 'movie', 'Dirty Movie', 'Dirty Movie', 0)"
            )
        )

    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    sources = {
        "name.basics.tsv.gz": write_gz(
            source_dir / "name.basics.tsv.gz",
            [
                "nconst\tprimaryName\tbirthYear\tdeathYear\tprimaryProfession\tknownForTitles",
                "nm0000001\tExample Person\t1980\t\\N\tactor,director\ttt0000001,tt0000002",
            ],
        ),
        "title.akas.tsv.gz": write_gz(
            source_dir / "title.akas.tsv.gz",
            [
                "titleId\tordering\ttitle\tregion\tlanguage\ttypes\tattributes\tisOriginalTitle",
                "tt0000001\t1\tExample Movie\tUS\ten\t\\N\t\\N\t1",
            ],
        ),
        "title.basics.tsv.gz": write_gz(
            source_dir / "title.basics.tsv.gz",
            [
                "tconst\ttitleType\tprimaryTitle\toriginalTitle\tisAdult\tstartYear\tendYear\truntimeMinutes\tgenres",
                "tt0000001\tmovie\tExample Movie\tExample Movie\t0\t2024\t\\N\t120\tDrama",
                "tt0000002\ttvEpisode\tExample Episode\tExample Episode\t0\t2024\t\\N\t45\tDrama,Short",
            ],
        ),
        "title.crew.tsv.gz": write_gz(
            source_dir / "title.crew.tsv.gz",
            [
                "tconst\tdirectors\twriters",
                "tt0000001\tnm0000001\tnm0000001",
            ],
        ),
        "title.episode.tsv.gz": write_gz(
            source_dir / "title.episode.tsv.gz",
            [
                "tconst\tparentTconst\tseasonNumber\tepisodeNumber",
                "tt0000002\ttt0000001\t1\t1",
            ],
        ),
        "title.principals.tsv.gz": write_gz(
            source_dir / "title.principals.tsv.gz",
            [
                "tconst\tordering\tnconst\tcategory\tjob\tcharacters",
                "tt0000001\t1\tnm0000001\tactor\t\\N\t[\"Lead\"]",
            ],
        ),
        "title.ratings.tsv.gz": write_gz(
            source_dir / "title.ratings.tsv.gz",
            [
                "tconst\taverageRating\tnumVotes",
                "tt0000001\t8.5\t1000",
            ],
        ),
    }

    def local_download(target_dir: Path, overwrite: bool = False) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename, source in sources.items():
            destination = target_dir / filename
            if destination.exists() and not overwrite:
                continue
            destination.write_bytes(source.read_bytes())

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DB_TEMPLATE_PATH", str(template_path))
    monkeypatch.setattr(docker_entrypoint, "download_imdb_data", local_download)

    docker_entrypoint.bootstrap_database()

    assert db_path.exists()
    assert list(data_dir.glob("*.tsv.gz")) == []

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM movies")).scalar_one() == 2
        assert conn.execute(text("SELECT COUNT(*) FROM people")).scalar_one() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM movie_ratings")).scalar_one() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM movie_principals")).scalar_one() == 1
        assert conn.execute(text("SELECT value FROM app_state WHERE key = 'bootstrap_complete'")).scalar_one() == "true"
        assert conn.execute(text("SELECT COUNT(*) FROM movies WHERE id = 'ttdirty0001'")).scalar_one() == 0
        index_names = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'")
            )
        }
        assert "idx_movies_type_year" in index_names
        assert "idx_ratings_votes_rating" in index_names

    docker_entrypoint.bootstrap_database()


def test_bootstrap_recovers_when_app_state_table_is_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "recommendation.db"
    data_dir = tmp_path / "imdb"

    calls: list[str] = []

    def fake_download(target_dir: Path, overwrite: bool = False) -> None:
        calls.append("download")
        assert target_dir == data_dir
        target_dir.mkdir(parents=True, exist_ok=True)

    def fake_import(database_url: str, import_data_dir: Path, **kwargs) -> None:
        calls.append("import")
        assert database_url == f"sqlite:///{db_path}"
        assert import_data_dir == data_dir
        assert kwargs["reset"] is False
        assert kwargs["prepare_schema"] is False
        assert kwargs["rebuild_indexes"] is True

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setattr(docker_entrypoint, "download_imdb_data", fake_download)
    monkeypatch.setattr(docker_entrypoint, "import_imdb_data", fake_import)

    docker_entrypoint.bootstrap_database()

    assert calls == ["download", "import"]
    with create_engine(f"sqlite:///{db_path}").connect() as conn:
        assert conn.execute(text("SELECT value FROM app_state WHERE key = 'bootstrap_complete'")).scalar_one() == "true"


def test_download_file_urls_are_configured():
    assert set(IMDB_FILES) == {
        "name.basics.tsv.gz",
        "title.akas.tsv.gz",
        "title.basics.tsv.gz",
        "title.crew.tsv.gz",
        "title.episode.tsv.gz",
        "title.principals.tsv.gz",
        "title.ratings.tsv.gz",
    }
