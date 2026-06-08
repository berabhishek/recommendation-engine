# Recommendation Engine

FastAPI + SQLAlchemy movie recommendation service built from IMDb gzip exports.

## Features

- Python rewrite of the app and importer
- Normalized relational schema for movies, people, ratings, genres, principals, crew, aka titles, and episodes
- Full gzip import into a fresh database

### API Endpoints

- `GET /health` - Health check endpoint.
- `GET /movies` - List movies with support for filtering, sorting, and pagination.
  - Query parameters:
    - `page` (default 1) - Page number.
    - `pageSize` (default 25) - Items per page.
    - `sortBy` (default `rating`) - Sort results (`title`, `year`, `rating`, `votes`, `runtime`).
    - `sortDir` (default `desc`) - Sort direction (`asc`, `desc`).
    - `q` - Text search on primary and original title.
    - `titleType` - Filter by title type.
    - `genres` - Comma-separated list of genres.
    - `yearMin`, `yearMax` - Filter by start year range.
    - `minRating`, `minVotes` - Filter by rating/votes.
- `GET /movies/{movie_id}` - Get detailed information about a specific movie.
- `POST /recommendations` - Get recommendations based on selected movies.
  - Body parameters:
    - `selectedMovieIds` - List of movie IDs (required).
    - `limit` - Limit of recommendations to return (default 20).
    - `page` - Page number.
    - `pageSize` - Items per page.

## Database choice

This first PR uses SQLite as the embedded database because the entire data set is local to the workspace and the goal is a self-contained base release that can be imported and queried without external infrastructure. The schema is normalized and portable, so it can move to PostgreSQL later if we want stronger concurrent write throughput or managed deployment.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python scripts/import_imdb.py
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The importer reads files from `raw data/` and rebuilds `data/recommendation.db`.

You can also pass additional arguments to the importer script:
- `--database-url`: The database URL (defaults to `sqlite:///data/recommendation.db`).
- `--data-dir`: The directory containing raw IMDb gzip files.
- `--no-reset`: Keep the existing database schema and data (skips dropping and recreating tables).
