from __future__ import annotations

import os
import shutil
import tempfile
from argparse import ArgumentParser
from pathlib import Path
import sys
from urllib.request import urlopen

from app.progress import ProgressBar


IMDB_FILES: dict[str, str] = {
    "name.basics.tsv.gz": "https://datasets.imdbws.com/name.basics.tsv.gz",
    "title.akas.tsv.gz": "https://datasets.imdbws.com/title.akas.tsv.gz",
    "title.basics.tsv.gz": "https://datasets.imdbws.com/title.basics.tsv.gz",
    "title.crew.tsv.gz": "https://datasets.imdbws.com/title.crew.tsv.gz",
    "title.episode.tsv.gz": "https://datasets.imdbws.com/title.episode.tsv.gz",
    "title.principals.tsv.gz": "https://datasets.imdbws.com/title.principals.tsv.gz",
    "title.ratings.tsv.gz": "https://datasets.imdbws.com/title.ratings.tsv.gz",
}


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        with urlopen(url) as response, temp_path.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        temp_path.replace(destination)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def download_imdb_data(
    target_dir: Path,
    overwrite: bool = False,
    progress: ProgressBar | None = None,
) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    pending: list[tuple[str, str, Path]] = []
    for filename, url in IMDB_FILES.items():
        destination = target_dir / filename
        if destination.exists() and not overwrite:
            continue
        pending.append((filename, url, destination))

    if progress is not None:
        progress.update_total(len(pending))
        progress.update_label("downloading")

    for filename, url, destination in pending:
        if progress is None:
            print(f"downloading {filename}", flush=True)
        download_file(url, destination)
        if progress is not None:
            progress.advance(1, label=filename)


def main(argv: list[str] | None = None) -> None:
    parser = ArgumentParser(description="Download IMDb gzip data files.")
    parser.add_argument("--data-dir", default=os.getenv("IMDB_DATA_DIR", "/data/imdb-data"))
    parser.add_argument("--overwrite", action="store_true", default=os.getenv("IMDB_DOWNLOAD_OVERWRITE", "0") == "1")
    parser.add_argument("--progress", dest="progress", action="store_true")
    parser.add_argument("--no-progress", dest="progress", action="store_false")
    parser.set_defaults(progress=None)
    args = parser.parse_args(argv)

    progress = None
    if args.progress is True or (args.progress is None and sys.stdout.isatty()):
        progress = ProgressBar(total=0, label="downloading")

    with progress or _NullContext() as bar:
        download_imdb_data(Path(args.data_dir), overwrite=args.overwrite, progress=bar)


class _NullContext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


if __name__ == "__main__":
    main()
