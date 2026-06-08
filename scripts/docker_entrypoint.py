from __future__ import annotations

import os
import sys
from pathlib import Path

from app.database import ensure_parent_dir
from app.importer import import_imdb_data
from scripts.download_imdb_data import download_imdb_data


DEFAULT_DATABASE_URL = "sqlite:////data/recommendation.db"
DEFAULT_DATA_DIR = "/data/imdb-data"
DEFAULT_TEMPLATE_PATH = "/opt/db-template/recommendation.db"
DEFAULT_MARKER_PATH = "/data/.initialized"


def sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(f"Unsupported database URL: {database_url}")
    return Path(database_url.removeprefix(prefix))


def bootstrap_database() -> None:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    data_dir = Path(os.getenv("DATA_DIR", DEFAULT_DATA_DIR))
    template_path = Path(os.getenv("DB_TEMPLATE_PATH", DEFAULT_TEMPLATE_PATH))
    marker_path = Path(os.getenv("DB_INIT_MARKER", DEFAULT_MARKER_PATH))
    db_path = sqlite_path_from_url(database_url)

    if marker_path.exists() and db_path.exists():
        return

    ensure_parent_dir(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if template_path.exists() and not db_path.exists():
        import shutil

        shutil.copy2(template_path, db_path)

    download_imdb_data(data_dir)

    import_imdb_data(
        database_url,
        data_dir,
        reset=False,
        prepare_schema=False,
        rebuild_indexes=True,
    )
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("initialized\n", encoding="utf-8")


def main(argv: list[str]) -> None:
    bootstrap_database()
    command = argv or ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
    os.execvp(command[0], command)


if __name__ == "__main__":
    main(sys.argv[1:])
