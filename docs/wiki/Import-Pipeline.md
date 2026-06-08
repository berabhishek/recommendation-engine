# Import Pipeline

The importer loads the IMDb source files into SQLite using a streaming approach so large datasets can be processed without holding them all in memory.

## Input Files

The import task expects gzip-compressed TSV files in `raw data/`:

- `title.basics.tsv.gz`
- `name.basics.tsv.gz`
- `title.ratings.tsv.gz`
- `title.principals.tsv.gz`
- `title.akas.tsv.gz`
- `title.crew.tsv.gz`
- `title.episode.tsv.gz`

## Process

1. Open the file as a stream.
2. Decompress it with `gunzip`.
3. Skip the header row.
4. Split each line on tabs.
5. Map the row into a typed record.
6. Upsert the record into SQLite.
7. Commit the full import only if every file succeeds.

## Why It Works Well

- Streaming keeps memory usage low.
- A single transaction makes imports safer and faster.
- Upserts let repeated imports refresh the local database without manual cleanup.

## Operational Notes

- The database file is `database.sqlite`.
- Re-running the importer is safe for the tables that use `INSERT OR REPLACE`.
- The import script prints a progress message every 100,000 rows for the larger files.
