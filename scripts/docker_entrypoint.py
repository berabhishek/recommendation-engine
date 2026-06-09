from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import ensure_parent_dir, get_engine, recreate_schema
from app.importer import import_imdb_data
from scripts.download_imdb_data import download_imdb_data


DEFAULT_DATABASE_URL = "sqlite:////data/recommendation.db"
DEFAULT_DATA_DIR = "/data/imdb-data"
DEFAULT_TEMPLATE_PATH = "/opt/db-template/recommendation.db"
BOOTSTRAP_COMPLETE_KEY = "bootstrap_complete"
IMDB_GZ_PATTERN = "*.tsv.gz"


def sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(f"Unsupported database URL: {database_url}")
    return Path(database_url.removeprefix(prefix))


def cleanup_downloaded_imdb_files(data_dir: Path) -> None:
    for path in data_dir.glob(IMDB_GZ_PATTERN):
        if path.is_file():
            path.unlink()


def bootstrap_database() -> None:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    data_dir = Path(os.getenv("DATA_DIR", DEFAULT_DATA_DIR))
    template_path = Path(os.getenv("DB_TEMPLATE_PATH", DEFAULT_TEMPLATE_PATH))
    db_path = sqlite_path_from_url(database_url)

    ensure_parent_dir(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if template_path.exists() and not db_path.exists():
        shutil.copy2(template_path, db_path)

    check_engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        with check_engine.connect() as conn:
            initialized = conn.execute(
                text("SELECT 1 FROM app_state WHERE key = :key"),
                {"key": BOOTSTRAP_COMPLETE_KEY},
            ).scalar_one_or_none()
    except OperationalError:
        initialized = None
    finally:
        check_engine.dispose()
    if initialized is not None:
        return

    if db_path.exists():
        db_path.unlink()
    if template_path.exists():
        shutil.copy2(template_path, db_path)

    runtime_engine = get_engine(database_url, apply_sqlite_pragmas=False)
    recreate_schema(runtime_engine, drop_existing=False)

    download_imdb_data(data_dir)

    import_imdb_data(
        database_url,
        data_dir,
        reset=False,
        prepare_schema=False,
        rebuild_indexes=True,
    )
    cleanup_downloaded_imdb_files(data_dir)
    with runtime_engine.begin() as conn:
        conn.execute(
            text("INSERT OR REPLACE INTO app_state (key, value) VALUES (:key, :value)"),
            {"key": BOOTSTRAP_COMPLETE_KEY, "value": "true"},
        )
    runtime_engine.dispose()


def main(argv: list[str]) -> None:
    bootstrap_database()
    command = argv or ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
    os.execvp(command[0], command)


if __name__ == "__main__":
    main(sys.argv[1:])
