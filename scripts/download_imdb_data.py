from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen


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


def download_imdb_data(target_dir: Path, overwrite: bool = False) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, url in IMDB_FILES.items():
        destination = target_dir / filename
        if destination.exists() and not overwrite:
            continue
        print(f"downloading {filename}", flush=True)
        download_file(url, destination)


def main() -> None:
    target_dir = Path(os.getenv("IMDB_DATA_DIR", "/data/imdb-data"))
    overwrite = os.getenv("IMDB_DOWNLOAD_OVERWRITE", "0") == "1"
    download_imdb_data(target_dir, overwrite=overwrite)


if __name__ == "__main__":
    main()
