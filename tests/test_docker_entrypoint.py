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
    data_dir = tmp_path / "imdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    recreate_schema(create_engine(f"sqlite:///{db_path}"), drop_existing=False)

    calls: list[str] = []

    def fake_download(target_dir: Path, overwrite: bool = False) -> None:
        calls.append("download")
        assert target_dir == data_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "title.ratings.tsv.gz").write_bytes(b"data")

    def fake_import(database_url: str, import_data_dir: Path, **kwargs) -> int:
        calls.append("import")
        assert database_url == f"sqlite:///{db_path}"
        assert import_data_dir == data_dir
        assert kwargs["reset"] is False
        assert kwargs["prepare_schema"] is False
        assert kwargs["rebuild_indexes"] is True
        return 1

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setattr(docker_entrypoint, "download_imdb_data", fake_download)
    monkeypatch.setattr(docker_entrypoint, "import_imdb_data", fake_import)

    docker_entrypoint.bootstrap_database()

    assert calls == ["download", "import"]
    with create_engine(f"sqlite:///{db_path}").connect() as conn:
        assert conn.execute(text("SELECT value FROM app_state WHERE key = 'bootstrap_complete'")).scalar_one() == "true"
        assert conn.execute(text("SELECT COUNT(*) FROM import_runs")).scalar_one() == 1
        assert conn.execute(text("SELECT status FROM import_runs ORDER BY id DESC LIMIT 1")).scalar_one() == "succeeded"
    assert list(data_dir.glob("*.tsv.gz")) == []

    docker_entrypoint.bootstrap_database()
    assert calls == ["download", "import"]


def test_bootstrap_stamps_existing_current_schema_before_importing(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "recommendation.db"
    data_dir = tmp_path / "imdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    recreate_schema(create_engine(f"sqlite:///{db_path}"), drop_existing=False)

    with create_engine(f"sqlite:///{db_path}").begin() as conn:
        conn.execute(
            text(
                "INSERT INTO movies (id, title_type, primary_title, original_title, genres_text, is_adult) "
                "VALUES ('ttdirty0001', 'movie', 'Dirty Movie', 'Dirty Movie', 'Drama', 0)"
            )
        )

    calls: list[str] = []

    def fake_download(target_dir: Path, overwrite: bool = False) -> None:
        calls.append("download")
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename in IMDB_FILES:
            write_gz(target_dir / filename, ["header"])

    def fake_import(database_url: str, import_data_dir: Path, **kwargs) -> int:
        calls.append("import")
        assert database_url == f"sqlite:///{db_path}"
        assert import_data_dir == data_dir
        assert kwargs["reset"] is False
        assert kwargs["prepare_schema"] is False
        assert kwargs["rebuild_indexes"] is True
        return 7

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setattr(docker_entrypoint, "download_imdb_data", fake_download)
    monkeypatch.setattr(docker_entrypoint, "import_imdb_data", fake_import)

    docker_entrypoint.bootstrap_database()

    assert calls == ["download", "import"]
    with create_engine(f"sqlite:///{db_path}").connect() as conn:
        movie_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(movies)"))}
        assert "genres_text" in movie_columns
        assert conn.execute(text("SELECT COUNT(*) FROM movies WHERE id = 'ttdirty0001'")).scalar_one() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM import_runs")).scalar_one() == 1
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
