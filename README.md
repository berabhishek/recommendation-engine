# Recommendation Engine

FastAPI + SQLAlchemy movie recommendation service backed by a SQLite database populated from IMDb gzip exports.

## Overview

This repository has two main workflows:

- Docker-first bootstrap for a self-contained first run
- Local development with a virtual environment and the import scripts

The app exposes the following REST API endpoints:

- `GET /health`
  - Returns `{"status": "ok"}`
- `GET /movies`
  - Returns a paginated list of movies.
  - Query parameters:
    - `page` (int, default: 1): The page number.
    - `pageSize` (int, default: 25, max: 100): The number of movies per page.
    - `sortBy` (str, default: "rating"): Sorting column ("title", "year", "rating", "votes", "runtime").
    - `sortDir` (str, default: "desc"): Sort direction ("asc" or "desc").
    - `q` (str, optional): Search term for primary or original titles.
    - `titleType` (str, optional): Filter by title type.
    - `genres` (str, optional): Comma-separated list of genres to filter by.
    - `yearMin` (int, optional): Minimum start year.
    - `yearMax` (int, optional): Maximum start year.
    - `minRating` (float, optional): Minimum average rating.
    - `minVotes` (int, optional): Minimum number of votes.
- `GET /movies/{movie_id}`
  - Returns detailed information about a specific movie, including its cast and crew.
- `POST /recommendations`
  - Returns a list of movie recommendations based on a selection of movies.
  - Payload:
    - `selectedMovieIds` (list[str]): Required. A list of one or more movie IDs.
    - `limit` (int, default: 20): The number of top recommendations.
    - `page` (int, default: 1): The page number.
    - `pageSize` (int, default: 20): The number of items per page.

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

If you want to run the app without Docker:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Import the IMDb data

The importer reads gzip files from `raw data/` by default and rebuilds `data/recommendation.db`.

```bash
.venv/bin/python scripts/import_imdb.py
```

Optional flags:

- `--database-url` (str): Override the target database URL (default from environment or `data/recommendation.db`).
- `--data-dir` (str): Provide an alternate directory for input `.tsv.gz` files.
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

Optional flags:

- `--data-dir` (str): Override the download directory (default `/data/imdb-data` if inside docker or configured by env).
- `--overwrite`: Force re-download even if the target file already exists.
- `--progress`: Force showing the download progress bar.
- `--no-progress`: Disable the progress bar.

By default this downloads into `/data/imdb-data` when run in the container, or into the directory you provide via `--data-dir`.

## Environment Variables

These are the main runtime settings:

- `DATABASE_URL`: SQLite URL for the application database. Default for Docker is `sqlite:////data/recommendation.db`.
- `DATA_DIR`: Directory used for IMDb downloads and import input.
- `DB_TEMPLATE_PATH`: Template SQLite database path used during Docker build and bootstrap.
- `IMDB_DATA_DIR`: Default download directory for `scripts/download_imdb_data.py`.
- `IMDB_DOWNLOAD_OVERWRITE`: Set to `1` to re-download existing IMDb files when using the download script.
- `DEFAULT_PAGE_SIZE`: Default page size for list endpoints.
- `MAX_PAGE_SIZE`: Maximum page size accepted by list endpoints.

## Testing

Test dependencies are managed in `pyproject.toml` using `[dev]` optional dependencies.

To run tests and check code coverage:

```bash
PYTHONPATH=. .venv/bin/pytest --cov=app --cov=scripts --cov-report=term-missing
```

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
