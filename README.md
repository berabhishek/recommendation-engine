# Recommendation Engine

FastAPI + SQLAlchemy movie recommendation service backed by a SQLite database populated from IMDb gzip exports.

## Overview

This repository has two main workflows:

- Docker-first bootstrap for a self-contained first run
- Local development with a virtual environment and the import scripts

The app exposes:

- `GET /health`
- `GET /movies`: Query parameters include `page`, `pageSize`, `sortBy`, `sortDir`, `q`, `titleType`, `genres`, `yearMin`, `yearMax`, `minRating`, `minVotes`.
- `GET /movies/{movie_id}`
- `POST /recommendations`: Payload fields include `selectedMovieIds`, `limit`, `page`, `pageSize`.

## Recommended Start

Use Docker if you want the full bootstrap handled for you.

```bash
docker compose up --build
```

On the first run this will:

1. Build the image.
2. Create a blank SQLite template during image build.
3. Start the container.
4. Detect that the database is not initialized yet.
5. Download the IMDb `.tsv.gz` files into `/data/imdb-data`.
6. Import the data into `/data/recommendation.db`.
7. Remove the downloaded `.tsv.gz` files after the import completes.
8. Mark bootstrap as complete and launch the API server on port `3000`.

After the first successful run, the same command will reuse the named volume and skip the download/import step.

Useful follow-up commands:

```bash
docker compose up
docker compose start
docker compose logs -f
```

## Local Development

If you want to run the app without Docker, make sure you have Python >= 3.10:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Testing

Tests and code coverage can be executed and verified using the command:

```bash
.venv/bin/pytest --cov=app --cov=scripts --cov-report=term-missing
```

### Import the IMDb data

The importer reads gzip files from `raw data/` by default and rebuilds `data/recommendation.db`.

```bash
.venv/bin/python scripts/import_imdb.py
```

Optional flags:

- `--database-url`: Set a custom SQLite connection string.
- `--data-dir`: Set a custom path to read IMDb gzip files from.
- `--no-reset` keeps the existing database file and schema.
- `--progress` forces the CLI progress bar.
- `--no-progress` disables the progress bar.

### Run the API

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## Downloading IMDb Data Manually

If you want to fetch the IMDb exports yourself instead of relying on Docker bootstrap:

```bash
.venv/bin/python scripts/download_imdb_data.py
```

By default this downloads into `/data/imdb-data` when run in the container, or into the directory you provide via `--data-dir`.

Optional flags:

- `--overwrite`: Re-download existing IMDb files.
- `--progress`: Show a progress bar.
- `--no-progress`: Disable the progress bar.

## Environment Variables

These are the main runtime settings:

- `DATABASE_URL`: SQLite URL for the application database. Default for Docker is `sqlite:////data/recommendation.db`.
- `DATA_DIR`: Directory used for IMDb downloads and import input.
- `DB_TEMPLATE_PATH`: Template SQLite database path used during Docker build and bootstrap.
- `IMDB_DATA_DIR`: Default download directory for `scripts/download_imdb_data.py`.
- `IMDB_DOWNLOAD_OVERWRITE`: Set to `1` to re-download existing IMDb files when using the download script.
- `DEFAULT_PAGE_SIZE`: Default page size for list endpoints.
- `MAX_PAGE_SIZE`: Maximum page size accepted by list endpoints.

## Repository Layout

- [`app/`](app/)
- [`scripts/`](scripts/)
- [`tests/`](tests/)
- [`docker-compose.yml`](docker-compose.yml)
- [`Dockerfile`](Dockerfile)

## Notes

- The SQLite database is stored on the Docker named volume mounted at `/data`.
- The downloaded IMDb gzip files are removed after a successful Docker bootstrap import, so the volume only keeps the database state.
- If the database exists but bootstrap has not been completed, the container resets it from the template before importing again.
