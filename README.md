# Recommendation Engine

FastAPI + SQLAlchemy movie recommendation service built from IMDb gzip exports.

## What this PR delivers

- Python rewrite of the app and importer
- Normalized relational schema for movies, people, ratings, genres, principals, crew, aka titles, and episodes
- Full gzip import into a fresh database
- `GET /health`
- `GET /movies` with filtering, sorting, and pagination
- `GET /movies/{movie_id}`
- `POST /recommendations`

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
