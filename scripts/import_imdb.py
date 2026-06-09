from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.importer import import_imdb_data
from app.progress import ProgressBar
from app.settings import DATABASE_URL, DATA_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Import IMDb gzip data into the recommendation database.")
    parser.add_argument("--database-url", default=DATABASE_URL)
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--no-reset", action="store_true", help="Keep the existing database schema and data.")
    parser.add_argument("--progress", dest="progress", action="store_true", help="Show a progress bar.")
    parser.add_argument("--no-progress", dest="progress", action="store_false", help="Disable the progress bar.")
    parser.set_defaults(progress=None)
    args = parser.parse_args()

    progress = None
    if args.progress is True or (args.progress is None and sys.stdout.isatty()):
        progress = ProgressBar(total=0, label="counting rows")

    with progress or _NullContext() as bar:
        import_imdb_data(
            args.database_url,
            Path(args.data_dir),
            reset=not args.no_reset,
            progress=bar,
        )


class _NullContext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


if __name__ == "__main__":
    main()
