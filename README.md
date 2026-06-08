# Recommendation Engine

An IMDb-backed recommendation and catalog API for movies and shows, built with Deno, Express, and SQLite.

The project ingests IMDb TSV exports into a local database, exposes CRUD endpoints for the core entities, and provides a ranked recommendations endpoint for title discovery. It also ships with a Swagger UI so the API can be explored without writing a client first.

## What this project does

- Imports IMDb-style datasets into SQLite
- Serves paginated CRUD APIs for titles, names, ratings, principals, akas, crew, and episodes
- Exposes a `/api/recommendations/titles` endpoint for ranked title discovery
- Provides an OpenAPI view at `/apidocs`
- Uses a simple local SQLite database so development stays fast and reproducible

## Tech Stack

- Deno
- Express
- SQLite
- Swagger UI

## Project Layout

- `server.ts` - HTTP server, routing, OpenAPI spec, and recommendation endpoint
- `db.ts` - SQLite schema, record mappers, and upsert helpers
- `scripts/import_imdb.ts` - batch importer for IMDb TSV.GZ exports
- `raw data/` - local IMDb source files expected by the importer

## Requirements

- Deno installed locally
- IMDb data files placed in `raw data/` using the expected filenames

## Setup

1. Install or verify Deno.
2. Put the IMDb `.tsv.gz` files into `raw data/`.
3. Start the API:

```bash
deno task start
```

The server defaults to `http://localhost:3000`.

## Load Data

Import the IMDb datasets into the local SQLite database:

```bash
deno task import:data
```

The importer expects these files:

- `raw data/title.basics.tsv.gz`
- `raw data/name.basics.tsv.gz`
- `raw data/title.ratings.tsv.gz`
- `raw data/title.principals.tsv.gz`
- `raw data/title.akas.tsv.gz`
- `raw data/title.crew.tsv.gz`
- `raw data/title.episode.tsv.gz`

The database file is created as `database.sqlite` in the repo root.

## API Overview

The main resource groups are:

- `/api/titles`
- `/api/names`
- `/api/title_ratings`
- `/api/title_principals`
- `/api/title_akas`
- `/api/title_crew`
- `/api/title_episodes`
- `/api/recommendations/titles`

Each CRUD collection supports:

- `GET /resource`
- `GET /resource/:id`
- `POST /resource`
- `PUT /resource/:id`
- `DELETE /resource/:id`

## Recommendation Endpoint

`GET /api/recommendations/titles` returns ranked titles with pagination support.

Supported filters include:

- `genres`
- `titleType`
- `minRating`
- `minVotes`
- `limitYears`

Supported sorting includes:

- `sortBy=recommendationScore`
- `sortBy=averageRating`
- `sortBy=numVotes`
- `sortDirection=asc|desc`

## API Docs

Swagger UI is available at:

- `http://localhost:3000/apidocs`

## Wiki

The repo includes a wiki-style documentation set under `docs/wiki/`:

- [Home](docs/wiki/Home.md)
- [Architecture](docs/wiki/Architecture.md)
- [API Reference](docs/wiki/API.md)
- [Data Model](docs/wiki/Data-Model.md)
- [Import Pipeline](docs/wiki/Import-Pipeline.md)

## Development Notes

- `server.ts` initializes the database on startup.
- The CRUD endpoints are table-driven, which keeps the API surface consistent across entity types.
- The recommendation endpoint currently uses a deterministic weighted score over ratings and vote count, which makes it a good baseline for iterative improvements.

## Next Steps

Likely follow-up work:

- add automated tests for the API surface
- document example requests and responses
- evolve the recommendation scoring strategy
- split the wiki into a dedicated GitHub Wiki if you want that publishing workflow
