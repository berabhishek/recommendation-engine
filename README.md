# Recommendation Engine

FastAPI + SQLAlchemy movie recommendation service backed by a SQLite database populated from IMDb gzip exports.

## Overview

This repository has two main workflows:

- Docker-first bootstrap for a self-contained first run
- Local development with a virtual environment and the import scripts

The app exposes:

- `GET /health`
- `GET /movies`
- `GET /movies/{movie_id}`
- `POST /recommendations`

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

### Fast smoke test

For a much smaller fixture-backed database, run the dedicated test service:

```bash
docker compose --profile test run --rm recommendation-test
```

That service uses the committed gzip fixtures in [`tests/fixtures/imdb-test/`](tests/fixtures/imdb-test/) to build a `recommendation-test` SQLite database, runs `curl` checks against `/health`, `/movies`, `/movies/{movie_id}`, and `/recommendations`, and removes the temporary test database before exiting.

If you want to inspect the database after the smoke test, keep it with:

```bash
KEEP_TEST_DB=1 docker compose --profile test run --rm recommendation-test
```

That leaves `/data/recommendation-test.db` in the named test volume so you can open it manually afterward.

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
.venv/bin/pip install -e .
```

### Import the IMDb data

The importer reads gzip files from `raw data/` by default and rebuilds `data/recommendation.db`.

```bash
.venv/bin/python scripts/import_imdb.py
```

Optional flags:

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
- The smoke-test container uses the tiny fixture set under [`tests/fixtures/imdb-test/`](tests/fixtures/imdb-test/) so it does not need the full IMDb download.
- The smoke-test service can keep `recommendation-test.db` by setting `KEEP_TEST_DB=1`.
