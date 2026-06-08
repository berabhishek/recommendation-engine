# Architecture

The application is intentionally simple: a Deno entrypoint starts an Express server, the server talks directly to SQLite, and a separate importer loads IMDb source files into the local database.

## Runtime Flow

1. `server.ts` starts the HTTP server.
2. `initDB()` creates the schema and indexes if they do not already exist.
3. Request handlers read and write directly from `database.sqlite`.
4. The recommendation endpoint joins `titles` and `title_ratings` to rank results.

## Main Components

- `server.ts`
  - HTTP routes
  - pagination, filtering, and sorting
  - OpenAPI metadata
  - Swagger UI mount
- `db.ts`
  - schema creation
  - import record mappers
  - `INSERT OR REPLACE` helpers for bulk ingestion
- `scripts/import_imdb.ts`
  - reads compressed TSV files
  - streams them line by line
  - wraps the full import in a transaction

## Storage Layer

SQLite is the only persistent store. That keeps the project easy to run locally and avoids extra infrastructure during development.

The schema covers:

- `titles`
- `names`
- `title_ratings`
- `title_principals`
- `title_akas`
- `title_crew`
- `title_episodes`

Indexes are created for the most common access paths, especially title type, year, genres, ratings, and principal lookups.

## API Layer

The API is table-driven. Each entity gets the same CRUD contract, with column metadata used to keep the route implementation compact and consistent.

That design makes it straightforward to add or adjust entities without duplicating route logic.

## Recommendation Layer

The current recommendation endpoint is a deterministic baseline:

- filter by title type, genres, rating, votes, and age window
- compute a score from rating and vote count
- sort the result set and paginate it

That gives you a predictable platform for future ranking improvements such as personalized signals, collaborative filtering, content embeddings, or hybrid ranking.
