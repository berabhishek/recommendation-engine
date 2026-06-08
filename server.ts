import express from "express";
import swaggerUi from "swagger-ui-express";
import {
  buildPageResult,
  db,
  initDB,
  normalizePage,
  normalizePageSize,
  pagination
} from "./db.ts";

initDB();

const app = express();
const PORT = Number(Deno.env.get("PORT") ?? 3000);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const openApiSpec = {
  openapi: "3.0.3",
  info: {
    title: "Recommendation Engine API",
    version: "1.0.0",
    description: "Paginated CRUD API for IMDb-style datasets plus recommendations."
  },
  servers: [{ url: "http://localhost:3000" }],
  paths: {
    "/heartbeat": { get: { summary: "Health check", responses: { "200": { description: "ok" } } } },
    "/api/titles": { get: {}, post: {} },
    "/api/titles/{id}": { get: {}, put: {}, delete: {} },
    "/api/names": { get: {}, post: {} },
    "/api/names/{id}": { get: {}, put: {}, delete: {} },
    "/api/title_ratings": { get: {}, post: {} },
    "/api/title_ratings/{id}": { get: {}, put: {}, delete: {} },
    "/api/title_principals": { get: {}, post: {} },
    "/api/title_principals/{id}": { get: {}, put: {}, delete: {} },
    "/api/title_akas": { get: {}, post: {} },
    "/api/title_akas/{id}": { get: {}, put: {}, delete: {} },
    "/api/title_crew": { get: {}, post: {} },
    "/api/title_crew/{id}": { get: {}, put: {}, delete: {} },
    "/api/title_episodes": { get: {}, post: {} },
    "/api/title_episodes/{id}": { get: {}, put: {}, delete: {} },
    "/api/recommendations/titles": { get: {} }
  }
};

const TABLES = {
  titles: {
    table: "titles",
    id: "tconst",
    columns: [
      "tconst",
      "titleType",
      "primaryTitle",
      "originalTitle",
      "isAdult",
      "startYear",
      "endYear",
      "runtimeMinutes",
      "genres"
    ],
    editable: ["titleType", "primaryTitle", "originalTitle", "isAdult", "startYear", "endYear", "runtimeMinutes", "genres"]
  },
  names: {
    table: "names",
    id: "nconst",
    columns: ["nconst", "primaryName", "birthYear", "deathYear", "primaryProfession", "knownForTitles"],
    editable: ["primaryName", "birthYear", "deathYear", "primaryProfession", "knownForTitles"]
  },
  title_ratings: {
    table: "title_ratings",
    id: "tconst",
    columns: ["tconst", "averageRating", "numVotes"],
    editable: ["averageRating", "numVotes"]
  },
  title_principals: {
    table: "title_principals",
    id: "id",
    columns: ["id", "tconst", "ordering", "nconst", "category", "job", "characters"],
    editable: ["tconst", "ordering", "nconst", "category", "job", "characters"]
  },
  title_akas: {
    table: "title_akas",
    id: "id",
    columns: ["id", "titleId", "ordering", "title", "region", "language", "types", "attributes", "isOriginalTitle"],
    editable: ["titleId", "ordering", "title", "region", "language", "types", "attributes", "isOriginalTitle"]
  },
  title_crew: {
    table: "title_crew",
    id: "tconst",
    columns: ["tconst", "directors", "writers"],
    editable: ["directors", "writers"]
  },
  title_episodes: {
    table: "title_episodes",
    id: "tconst",
    columns: ["tconst", "parentTconst", "seasonNumber", "episodeNumber"],
    editable: ["parentTconst", "seasonNumber", "episodeNumber"]
  }
} as const;

type TableName = keyof typeof TABLES;
type Req = express.Request;
type Res = express.Response;

function jsonError(res: express.Response, status: number, message: string) {
  return res.status(status).json({ error: message });
}

function queryAll<T = Record<string, unknown>>(sql: string, args: unknown[] = []): T[] {
  return db.queryEntries(sql, args as any) as T[];
}

function queryOne<T = Record<string, unknown>>(sql: string, args: unknown[] = []): T | null {
  const rows = queryAll<T>(sql, args);
  return rows[0] ?? null;
}

function toNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseStringFilter(value: unknown) {
  if (typeof value !== "string" || !value.trim()) return undefined;
  return value.trim();
}

function parseCsv(value: unknown) {
  const raw = parseStringFilter(value);
  return raw ? raw.split(",").map((part) => part.trim()).filter(Boolean) : undefined;
}

function buildTitleWhere(params: Record<string, unknown>, alias = "titles") {
  const prefix = alias ? `${alias}.` : "";
  const clauses: string[] = [];
  const values: unknown[] = [];

  const titleType = parseStringFilter(params.titleType);
  if (titleType) {
    clauses.push(`${prefix}titleType = ?`);
    values.push(titleType);
  }
  const genre = parseStringFilter(params.genre);
  if (genre) {
    clauses.push(`${prefix}genres LIKE ?`);
    values.push(`%${genre}%`);
  }
  const q = parseStringFilter(params.q);
  if (q) {
    clauses.push(`(${prefix}primaryTitle LIKE ? OR ${prefix}originalTitle LIKE ?)`);
    values.push(`%${q}%`, `%${q}%`);
  }
  const minRating = parseStringFilter(params.minRating);
  if (minRating) {
    clauses.push(`r.averageRating >= ?`);
    values.push(Number(minRating));
  }
  const minVotes = parseStringFilter(params.minVotes);
  if (minVotes) {
    clauses.push(`r.numVotes >= ?`);
    values.push(Number(minVotes));
  }
  return { clause: clauses.length ? `WHERE ${clauses.join(" AND ")}` : "", values };
}

function buildNameWhere(params: Record<string, unknown>, alias = "names") {
  const prefix = alias ? `${alias}.` : "";
  const clauses: string[] = [];
  const values: unknown[] = [];
  const primaryName = parseStringFilter(params.primaryName);
  if (primaryName) {
    clauses.push(`${prefix}primaryName LIKE ?`);
    values.push(`%${primaryName}%`);
  }
  const profession = parseStringFilter(params.primaryProfession);
  if (profession) {
    clauses.push(`${prefix}primaryProfession LIKE ?`);
    values.push(`%${profession}%`);
  }
  const startYearMin = parseStringFilter(params.startYearMin);
  if (startYearMin) {
    clauses.push(`${prefix}birthYear >= ?`);
    values.push(Number(startYearMin));
  }
  const startYearMax = parseStringFilter(params.startYearMax);
  if (startYearMax) {
    clauses.push(`${prefix}birthYear <= ?`);
    values.push(Number(startYearMax));
  }
  const q = parseStringFilter(params.q);
  if (q) {
    clauses.push(`(${prefix}primaryName LIKE ? OR ${prefix}primaryProfession LIKE ?)`);
    values.push(`%${q}%`, `%${q}%`);
  }
  return { clause: clauses.length ? `WHERE ${clauses.join(" AND ")}` : "", values };
}

function applyOrdering(sortBy: string | undefined, sortDirection: string | undefined, allowed: string[], defaultSort: string) {
  const column = sortBy && allowed.includes(sortBy) ? sortBy : defaultSort;
  const direction = sortDirection?.toLowerCase() === "asc" ? "ASC" : "DESC";
  return `ORDER BY ${column} ${direction}`;
}

function crudRoutes(tableName: TableName) {
  const meta = TABLES[tableName];
  const base = `/api/${tableName}`;

  app.get(base, (req: Req, res: Res) => {
    const page = normalizePage(req.query.page);
    const pageSize = normalizePageSize(req.query.pageSize);
    const { limit, offset } = pagination({ page, pageSize });
    const sortBy = typeof req.query.sortBy === "string" ? req.query.sortBy : undefined;
    const sortDirection = typeof req.query.sortDirection === "string" ? req.query.sortDirection : undefined;
    let where = { clause: "", values: [] as unknown[] };
    let order = applyOrdering(sortBy, sortDirection, [...meta.columns], meta.columns[0]);
    let select = `SELECT ${meta.table}.*`;
    let joins = "";

    if (tableName === "titles") {
      where = buildTitleWhere(req.query);
      joins = `LEFT JOIN title_ratings r ON r.tconst = titles.tconst`;
      select = `SELECT titles.*, r.averageRating, r.numVotes`;
    } else if (tableName === "names") {
      where = buildNameWhere(req.query);
    } else if (tableName === "title_ratings") {
      joins = `INNER JOIN titles t ON t.tconst = title_ratings.tconst`;
      select = `SELECT title_ratings.*, t.primaryTitle, t.titleType, t.startYear, t.genres`;
      order = applyOrdering(sortBy, sortDirection, ["tconst", "averageRating", "numVotes"], "averageRating");
    }

    const sql = `${select} FROM ${meta.table} ${joins} ${where.clause} ${order} LIMIT ? OFFSET ?`;
    const countSql = `SELECT COUNT(*) as total FROM ${meta.table} ${joins} ${where.clause}`;
    const rows = queryAll(sql, [...where.values, limit, offset]);
    const total = queryOne<{ total: number }>(countSql, where.values)?.total ?? 0;
    res.json(buildPageResult(rows, total, page, pageSize));
  });

  app.get(`${base}/:id`, (req: Req, res: Res) => {
    const row = queryOne(`SELECT * FROM ${meta.table} WHERE ${meta.id} = ?`, [req.params.id]);
    if (!row) return jsonError(res, 404, `${tableName} record not found`);
    return res.json(row);
  });

  app.post(base, (req: Req, res: Res) => {
    const payload = req.body ?? {};
    const columns = meta.editable.filter((column) => payload[column] !== undefined);
    if (!payload[meta.id]) return jsonError(res, 400, `${meta.id} is required`);
    const insertColumns = [meta.id, ...columns];
    const placeholders = insertColumns.map(() => "?").join(", ");
    const values = insertColumns.map((column) => payload[column]);
    db.query(`INSERT OR REPLACE INTO ${meta.table} (${insertColumns.join(", ")}) VALUES (${placeholders})`, values);
    const row = queryOne(`SELECT * FROM ${meta.table} WHERE ${meta.id} = ?`, [payload[meta.id]]);
    res.status(201).json(row);
  });

  app.put(`${base}/:id`, (req: Req, res: Res) => {
    const payload = req.body ?? {};
    const columns = meta.editable.filter((column) => payload[column] !== undefined);
    if (!columns.length) return jsonError(res, 400, "No updatable fields provided");
    const assignments = columns.map((column) => `${column} = ?`).join(", ");
    db.query(`UPDATE ${meta.table} SET ${assignments} WHERE ${meta.id} = ?`, [...columns.map((column) => payload[column]), req.params.id]);
    const row = queryOne(`SELECT * FROM ${meta.table} WHERE ${meta.id} = ?`, [req.params.id]);
    if (!row) return jsonError(res, 404, `${tableName} record not found`);
    res.json(row);
  });

  app.delete(`${base}/:id`, (req: Req, res: Res) => {
    db.query(`DELETE FROM ${meta.table} WHERE ${meta.id} = ?`, [req.params.id]);
    res.status(204).send();
  });
}

Object.keys(TABLES).forEach((table) => crudRoutes(table as TableName));

app.get("/heartbeat", (_req: Req, res: Res) => res.json({ status: "ok" }));

app.get("/api/recommendations/titles", (req: Req, res: Res) => {
  const page = normalizePage(req.query.page);
  const pageSize = normalizePageSize(req.query.pageSize);
  const { limit, offset } = pagination({ page, pageSize });
  const genres = parseCsv(req.query.genres);
  const titleType = parseStringFilter(req.query.titleType);
  const minRating = toNumber(req.query.minRating, 0);
  const minVotes = toNumber(req.query.minVotes, 0);
  const limitYears = toNumber(req.query.limitYears, 0);
  const orderBy = typeof req.query.sortBy === "string" ? req.query.sortBy : "recommendationScore";
  const direction = typeof req.query.sortDirection === "string" && req.query.sortDirection.toLowerCase() === "asc" ? "ASC" : "DESC";
  const where: string[] = ["1=1"];
  const values: unknown[] = [];

  if (titleType) {
    where.push("t.titleType = ?");
    values.push(titleType);
  }
  if (genres?.length) {
    where.push(`(${genres.map(() => "t.genres LIKE ?").join(" OR ")})`);
    values.push(...genres.map((genre) => `%${genre}%`));
  }
  if (minRating) {
    where.push("r.averageRating >= ?");
    values.push(minRating);
  }
  if (minVotes) {
    where.push("r.numVotes >= ?");
    values.push(minVotes);
  }
  if (limitYears) {
    where.push("t.startYear >= strftime('%Y','now') - ?");
    values.push(limitYears);
  }

  const sql = `
    SELECT
      t.*,
      r.averageRating,
      r.numVotes,
      CASE
        WHEN r.numVotes IS NULL THEN 0
        ELSE (r.averageRating * (r.numVotes + 1))
      END AS recommendationScore
    FROM titles t
    LEFT JOIN title_ratings r ON r.tconst = t.tconst
    WHERE ${where.join(" AND ")}
    ORDER BY ${orderBy === "averageRating" ? "r.averageRating" : orderBy === "numVotes" ? "r.numVotes" : "recommendationScore"} ${direction}
    LIMIT ? OFFSET ?
  `;
  const countSql = `SELECT COUNT(*) as total FROM titles t LEFT JOIN title_ratings r ON r.tconst = t.tconst WHERE ${where.join(" AND ")}`;
  const rows = queryAll(sql, [...values, limit, offset]);
  const total = queryOne<{ total: number }>(countSql, values)?.total ?? 0;
  res.json(buildPageResult(rows, total, page, pageSize));
});

app.use("/apidocs", swaggerUi.serve, swaggerUi.setup(openApiSpec));

if (import.meta.main) {
  app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
}

export { app };
