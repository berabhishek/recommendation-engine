from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import ensure_parent_dir, get_engine
from app.importer import import_imdb_data
from app.migrations import get_current_database_revision, get_head_revision, upgrade_database
from scripts.download_imdb_data import IMDB_FILES, download_imdb_data


DEFAULT_DATABASE_URL = "sqlite:////data/recommendation.db"
DEFAULT_DATA_DIR = "/data/imdb-data"
BOOTSTRAP_COMPLETE_KEY = "bootstrap_complete"
IMPORTER_VERSION = "1"
DATASET_NAME = "imdb"
IMDB_GZ_PATTERN = "*.tsv.gz"
IMPORT_RUN_STATUS_RUNNING = "running"
IMPORT_RUN_STATUS_SUCCEEDED = "succeeded"
IMPORT_RUN_STATUS_FAILED = "failed"


def sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(f"Unsupported database URL: {database_url}")
    return Path(database_url.removeprefix(prefix))


def cleanup_downloaded_imdb_files(data_dir: Path) -> None:
    for path in data_dir.glob(IMDB_GZ_PATTERN):
        if path.is_file():
            path.unlink()


def get_dataset_version(data_dir: Path) -> str | None:
    required_files = [data_dir / filename for filename in sorted(IMDB_FILES)]
    if not all(path.exists() for path in required_files):
        return None

    digest = []
    for path in required_files:
        stat = path.stat()
        digest.append(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
    return "|".join(digest)


def get_latest_successful_import_run(database_url: str) -> dict[str, object] | None:
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, dataset_name, dataset_version, importer_version, alembic_revision, "
                    "status, started_at, finished_at, row_count, error_message "
                    "FROM import_runs "
                    "WHERE status = :status "
                    "ORDER BY id DESC "
                    "LIMIT 1"
                ),
                {"status": IMPORT_RUN_STATUS_SUCCEEDED},
            ).mappings().first()
            return dict(row) if row is not None else None
    except OperationalError:
        return None
    finally:
        engine.dispose()


def get_bootstrap_complete(database_url: str) -> bool:
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        with engine.connect() as conn:
            value = conn.execute(
                text("SELECT value FROM app_state WHERE key = :key"),
                {"key": BOOTSTRAP_COMPLETE_KEY},
            ).scalar_one_or_none()
            return value == "true"
    except OperationalError:
        return False
    finally:
        engine.dispose()


def set_bootstrap_complete(database_url: str, value: str = "true") -> None:
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT OR REPLACE INTO app_state (key, value) VALUES (:key, :value)"),
                {"key": BOOTSTRAP_COMPLETE_KEY, "value": value},
            )
    finally:
        engine.dispose()


def record_import_run_start(database_url: str, alembic_revision: str, dataset_version: str | None) -> int:
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        started_at = datetime.utcnow()
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO import_runs (dataset_name, dataset_version, importer_version, alembic_revision, "
                    "status, started_at) "
                    "VALUES (:dataset_name, :dataset_version, :importer_version, :alembic_revision, :status, :started_at)"
                ),
                {
                    "dataset_name": DATASET_NAME,
                    "dataset_version": dataset_version,
                    "importer_version": IMPORTER_VERSION,
                    "alembic_revision": alembic_revision,
                    "status": IMPORT_RUN_STATUS_RUNNING,
                    "started_at": started_at,
                },
            )
            return int(result.lastrowid or 0)
    finally:
        engine.dispose()


def finish_import_run(
    database_url: str,
    run_id: int,
    *,
    status: str,
    dataset_version: str | None = None,
    row_count: int | None = None,
    error_message: str | None = None,
) -> None:
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        finished_at = datetime.utcnow()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE import_runs "
                    "SET status = :status, finished_at = :finished_at, dataset_version = COALESCE(:dataset_version, dataset_version), "
                    "row_count = :row_count, "
                    "error_message = :error_message "
                    "WHERE id = :id"
                ),
                {
                    "id": run_id,
                    "status": status,
                    "finished_at": finished_at,
                    "dataset_version": dataset_version,
                    "row_count": row_count,
                    "error_message": error_message,
                },
            )
    finally:
        engine.dispose()


def bootstrap_database() -> None:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    data_dir = Path(os.getenv("DATA_DIR", DEFAULT_DATA_DIR))

    ensure_parent_dir(database_url)
    data_dir.mkdir(parents=True, exist_ok=True)

    upgrade_database(database_url)
    current_revision = get_current_database_revision(database_url) or get_head_revision(database_url)

    latest_run = get_latest_successful_import_run(database_url)
    if (
        get_bootstrap_complete(database_url)
        and latest_run is not None
        and latest_run["dataset_name"] == DATASET_NAME
        and latest_run["importer_version"] == IMPORTER_VERSION
        and latest_run["alembic_revision"] == current_revision
    ):
        return

    current_dataset_version = get_dataset_version(data_dir)

    needs_import = (
        latest_run is None
        or latest_run["dataset_name"] != DATASET_NAME
        or latest_run["importer_version"] != IMPORTER_VERSION
        or latest_run["alembic_revision"] != current_revision
        or latest_run["dataset_version"] != current_dataset_version
    )

    if not needs_import:
        if not get_bootstrap_complete(database_url):
            set_bootstrap_complete(database_url)
        return

    overwrite = latest_run is not None and current_dataset_version is not None and latest_run["dataset_version"] != current_dataset_version
    run_id = record_import_run_start(database_url, current_revision, current_dataset_version)

    try:
        download_imdb_data(data_dir, overwrite=overwrite)
        current_dataset_version = get_dataset_version(data_dir)

        row_count = import_imdb_data(
            database_url,
            data_dir,
            reset=False,
            prepare_schema=False,
        )
    except Exception as exc:
        finish_import_run(
            database_url,
            run_id,
            status=IMPORT_RUN_STATUS_FAILED,
            dataset_version=current_dataset_version,
            error_message=f"{type(exc).__name__}: {exc}",
        )
        raise
    else:
        finish_import_run(
            database_url,
            run_id,
            status=IMPORT_RUN_STATUS_SUCCEEDED,
            dataset_version=current_dataset_version,
            row_count=row_count,
        )
        cleanup_downloaded_imdb_files(data_dir)
        set_bootstrap_complete(database_url)


def main(argv: list[str]) -> None:
    bootstrap_database()
    command = argv or ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
    os.execvp(command[0], command)


if __name__ == "__main__":
    main(sys.argv[1:])
