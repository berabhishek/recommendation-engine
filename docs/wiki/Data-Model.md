# Data Model

The database schema is optimized for IMDb-style datasets and recommendation-style reads.

## Tables

- `titles`
  - core movie and show metadata
- `names`
  - people and creatives
- `title_ratings`
  - aggregated score and vote counts
- `title_principals`
  - cast and crew participation
- `title_akas`
  - alternate titles by region and language
- `title_crew`
  - director and writer lists
- `title_episodes`
  - episodic relationships

## Key Fields

- `tconst`
  - title identifier
- `nconst`
  - person identifier
- `isAdult`
  - adult-content flag
- `genres`
  - comma-separated genre list
- `averageRating`
  - numeric rating from IMDb data
- `numVotes`
  - vote count used for ranking

## Relationships

- `title_ratings.tconst` references `titles.tconst`
- `title_principals.tconst` references `titles.tconst`
- `title_principals.nconst` references `names.nconst`
- `title_akas.titleId` references `titles.tconst`
- `title_crew.tconst` references `titles.tconst`
- `title_episodes.tconst` references `titles.tconst`
- `title_episodes.parentTconst` references `titles.tconst`

## Index Strategy

The schema creates indexes for:

- `titles(titleType, startYear)`
- `titles(genres)`
- `title_ratings(numVotes)`
- `title_principals(tconst)`
- `title_principals(nconst)`
- `title_akas(titleId)`

These indexes support the most common filtering and recommendation queries.
