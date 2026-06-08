from __future__ import annotations

import argparse
from pathlib import Path

from app.importer import import_imdb_data
from app.settings import DATABASE_URL, DATA_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Import IMDb gzip data into the recommendation database.")
    parser.add_argument("--database-url", default=DATABASE_URL)
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--no-reset", action="store_true", help="Keep the existing database schema and data.")
    args = parser.parse_args()
    import_imdb_data(args.database_url, Path(args.data_dir), reset=not args.no_reset)


if __name__ == "__main__":
    main()
