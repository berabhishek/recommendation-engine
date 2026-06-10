from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

import scripts.docker_entrypoint as docker_entrypoint
from scripts.download_imdb_data import IMDB_FILES


def write_gz(path: Path, lines: list[str]) -> Path:
    import gzip

    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def test_bootstrap_runs_alembic_then_import_on_missing_database(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "recommendation.db"
    data_dir = tmp_path / "imdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    calls: list[str] = []

    def fake_download(target_dir: Path, overwrite: bool = False) -> None:
        calls.append("download")
        assert target_dir == data_dir
        assert overwrite is False
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename in IMDB_FILES:
            write_gz(target_dir / filename, ["header"])

    def fake_import(database_url: str, import_data_dir: Path, **kwargs) -> int:
        calls.append("import")
        assert database_url == f"sqlite:///{db_path}"
        assert import_data_dir == data_dir
        assert kwargs == {"reset": False, "prepare_schema": False}
        return 1

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setattr(docker_entrypoint, "download_imdb_data", fake_download)
    monkeypatch.setattr(docker_entrypoint, "import_imdb_data", fake_import)

    docker_entrypoint.bootstrap_database()

    assert calls == ["download", "import"]
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        inspector = inspect(engine)
        assert "alembic_version" in inspector.get_table_names()
        assert "import_runs" in inspector.get_table_names()
        assert "movies" in inspector.get_table_names()
        assert "app_state" in inspector.get_table_names()

        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM import_runs")).scalar_one() == 1
            assert conn.execute(text("SELECT status FROM import_runs ORDER BY id DESC LIMIT 1")).scalar_one() == "succeeded"
            assert conn.execute(text("SELECT value FROM app_state WHERE key = 'bootstrap_complete'")).scalar_one() == "true"
    finally:
        engine.dispose()

    assert list(data_dir.glob("*.tsv.gz")) == []

    docker_entrypoint.bootstrap_database()
    assert calls == ["download", "import"]
