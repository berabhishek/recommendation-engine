from __future__ import annotations

from pathlib import Path

import scripts.download_imdb_data as download_imdb_data


def test_download_imdb_data_downloads_files_serially(tmp_path, monkeypatch):
    monkeypatch.setattr(
        download_imdb_data,
        "IMDB_FILES",
        {
            "one.tsv.gz": "https://example.com/one",
            "two.tsv.gz": "https://example.com/two",
        },
    )

    calls: list[str] = []

    def fake_download(url: str, destination: Path) -> None:
        calls.append(destination.name)
        destination.write_text(url)

    monkeypatch.setattr(download_imdb_data, "download_file", fake_download)

    download_imdb_data.download_imdb_data(tmp_path, overwrite=True)

    assert calls == ["one.tsv.gz", "two.tsv.gz"]
