# API Reference

All endpoints are served from the same Express application. Responses are JSON unless otherwise noted.

## Conventions

- Pagination:
  - `page`
  - `pageSize`
- Sorting:
  - `sortBy`
  - `sortDirection=asc|desc`
- Filtering:
  - each collection exposes entity-specific query parameters

`pageSize` is capped server-side at 100.

## Health

- `GET /heartbeat`

Returns:

```json
{ "status": "ok" }
```

## CRUD Collections

Each collection supports:

- `GET /api/<resource>`
- `GET /api/<resource>/:id`
- `POST /api/<resource>`
- `PUT /api/<resource>/:id`
- `DELETE /api/<resource>/:id`

Supported resources:

- `titles`
- `names`
- `title_ratings`
- `title_principals`
- `title_akas`
- `title_crew`
- `title_episodes`

## Titles

`GET /api/titles`

Useful query parameters:

- `q`
- `titleType`
- `genre`
- `minRating`
- `minVotes`
- `sortBy`
- `sortDirection`

`titles` responses include joined rating fields when available.

## Names

`GET /api/names`

Useful query parameters:

- `q`
- `primaryName`
- `primaryProfession`
- `startYearMin`
- `startYearMax`

## Ratings

`GET /api/title_ratings`

This endpoint joins rating rows back to title metadata so clients can show a title context alongside the numeric score.

## Recommendations

`GET /api/recommendations/titles`

Useful query parameters:

- `genres`
- `titleType`
- `minRating`
- `minVotes`
- `limitYears`
- `sortBy`
- `sortDirection`

Example:

```bash
curl "http://localhost:3000/api/recommendations/titles?genres=Drama,Thriller&minRating=7&minVotes=1000&page=1&pageSize=20"
```

## OpenAPI

Swagger UI is available at `/apidocs`.
