import { DB } from "sqlite";

export const db = new DB("database.sqlite");

export type SortDirection = "asc" | "desc";

export interface PageOptions {
  page: number;
  pageSize: number;
}

export interface ListOptions extends PageOptions {
  sortBy?: string;
  sortDirection?: SortDirection;
}

const DEFAULT_PAGE_SIZE = 25;

export function initDB() {
  db.execute(`
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS names (
      nconst TEXT PRIMARY KEY,
      primaryName TEXT NOT NULL,
      birthYear INTEGER,
      deathYear INTEGER,
      primaryProfession TEXT,
      knownForTitles TEXT
    );

    CREATE TABLE IF NOT EXISTS titles (
      tconst TEXT PRIMARY KEY,
      titleType TEXT NOT NULL,
      primaryTitle TEXT NOT NULL,
      originalTitle TEXT NOT NULL,
      isAdult INTEGER NOT NULL DEFAULT 0,
      startYear INTEGER,
      endYear INTEGER,
      runtimeMinutes INTEGER,
      genres TEXT
    );

    CREATE TABLE IF NOT EXISTS title_ratings (
      tconst TEXT PRIMARY KEY,
      averageRating REAL NOT NULL,
      numVotes INTEGER NOT NULL,
      FOREIGN KEY (tconst) REFERENCES titles(tconst) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS title_principals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      tconst TEXT NOT NULL,
      ordering INTEGER NOT NULL,
      nconst TEXT NOT NULL,
      category TEXT,
      job TEXT,
      characters TEXT,
      FOREIGN KEY (tconst) REFERENCES titles(tconst) ON DELETE CASCADE,
      FOREIGN KEY (nconst) REFERENCES names(nconst) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS title_akas (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      titleId TEXT NOT NULL,
      ordering INTEGER NOT NULL,
      title TEXT NOT NULL,
      region TEXT,
      language TEXT,
      types TEXT,
      attributes TEXT,
      isOriginalTitle INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY (titleId) REFERENCES titles(tconst) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS title_crew (
      tconst TEXT PRIMARY KEY,
      directors TEXT,
      writers TEXT,
      FOREIGN KEY (tconst) REFERENCES titles(tconst) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS title_episodes (
      tconst TEXT PRIMARY KEY,
      parentTconst TEXT NOT NULL,
      seasonNumber INTEGER,
      episodeNumber INTEGER,
      FOREIGN KEY (tconst) REFERENCES titles(tconst) ON DELETE CASCADE,
      FOREIGN KEY (parentTconst) REFERENCES titles(tconst) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_titles_type_year ON titles(titleType, startYear);
    CREATE INDEX IF NOT EXISTS idx_titles_genres ON titles(genres);
    CREATE INDEX IF NOT EXISTS idx_ratings_votes ON title_ratings(numVotes);
    CREATE INDEX IF NOT EXISTS idx_principals_tconst ON title_principals(tconst);
    CREATE INDEX IF NOT EXISTS idx_principals_nconst ON title_principals(nconst);
    CREATE INDEX IF NOT EXISTS idx_akas_title ON title_akas(titleId);
  `);
}

export function normalizePage(page: number | string | undefined) {
  const value = Number(page ?? 1);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 1;
}

export function normalizePageSize(pageSize: number | string | undefined) {
  const value = Number(pageSize ?? DEFAULT_PAGE_SIZE);
  if (!Number.isFinite(value) || value <= 0) return DEFAULT_PAGE_SIZE;
  return Math.min(100, Math.floor(value));
}

export function pagination({ page, pageSize }: PageOptions) {
  const offset = (page - 1) * pageSize;
  return { limit: pageSize, offset };
}

export function buildPageResult<T>(rows: T[], total: number, page: number, pageSize: number) {
  return {
    data: rows,
    meta: {
      page,
      pageSize,
      total,
      totalPages: Math.max(1, Math.ceil(total / pageSize))
    }
  };
}

function parseList(value: string | null | undefined) {
  if (!value || value === "\\N") return null;
  return value;
}

function parseIntOrNull(value: string | null | undefined) {
  if (!value || value === "\\N") return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseFloatOrNull(value: string | null | undefined) {
  if (!value || value === "\\N") return null;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseBool(value: string | null | undefined) {
  return value === "1" ? 1 : 0;
}

export interface TitleRecord {
  tconst: string;
  titleType: string;
  primaryTitle: string;
  originalTitle: string;
  isAdult: number;
  startYear: number | null;
  endYear: number | null;
  runtimeMinutes: number | null;
  genres: string | null;
}

export interface NameRecord {
  nconst: string;
  primaryName: string;
  birthYear: number | null;
  deathYear: number | null;
  primaryProfession: string | null;
  knownForTitles: string | null;
}

export interface RatingRecord {
  tconst: string;
  averageRating: number;
  numVotes: number;
}

export interface PrincipalRecord {
  tconst: string;
  ordering: number;
  nconst: string;
  category: string | null;
  job: string | null;
  characters: string | null;
}

export interface AkaRecord {
  titleId: string;
  ordering: number;
  title: string;
  region: string | null;
  language: string | null;
  types: string | null;
  attributes: string | null;
  isOriginalTitle: number;
}

export interface CrewRecord {
  tconst: string;
  directors: string | null;
  writers: string | null;
}

export interface EpisodeRecord {
  tconst: string;
  parentTconst: string;
  seasonNumber: number | null;
  episodeNumber: number | null;
}

export function mapTitle(parts: string[]): TitleRecord {
  return {
    tconst: parts[0],
    titleType: parts[1],
    primaryTitle: parts[2],
    originalTitle: parts[3],
    isAdult: Number(parts[4] ?? "0"),
    startYear: parseIntOrNull(parts[5]),
    endYear: parseIntOrNull(parts[6]),
    runtimeMinutes: parseIntOrNull(parts[7]),
    genres: parseList(parts[8])
  };
}

export function mapName(parts: string[]): NameRecord {
  return {
    nconst: parts[0],
    primaryName: parts[1],
    birthYear: parseIntOrNull(parts[2]),
    deathYear: parseIntOrNull(parts[3]),
    primaryProfession: parseList(parts[4]),
    knownForTitles: parseList(parts[5])
  };
}

export function mapRating(parts: string[]): RatingRecord {
  return {
    tconst: parts[0],
    averageRating: parseFloatOrNull(parts[1]) ?? 0,
    numVotes: parseIntOrNull(parts[2]) ?? 0
  };
}

export function mapPrincipal(parts: string[]): PrincipalRecord {
  return {
    tconst: parts[0],
    ordering: parseIntOrNull(parts[1]) ?? 0,
    nconst: parts[2],
    category: parseList(parts[3]),
    job: parseList(parts[4]),
    characters: parseList(parts[5])
  };
}

export function mapAka(parts: string[]): AkaRecord {
  return {
    titleId: parts[0],
    ordering: parseIntOrNull(parts[1]) ?? 0,
    title: parts[2],
    region: parseList(parts[3]),
    language: parseList(parts[4]),
    types: parseList(parts[5]),
    attributes: parseList(parts[6]),
    isOriginalTitle: parseBool(parts[7])
  };
}

export function mapCrew(parts: string[]): CrewRecord {
  return {
    tconst: parts[0],
    directors: parseList(parts[1]),
    writers: parseList(parts[2])
  };
}

export function mapEpisode(parts: string[]): EpisodeRecord {
  return {
    tconst: parts[0],
    parentTconst: parts[1],
    seasonNumber: parseIntOrNull(parts[2]),
    episodeNumber: parseIntOrNull(parts[3])
  };
}

export function upsertTitle(record: TitleRecord) {
  db.query(
    `INSERT OR REPLACE INTO titles
     (tconst, titleType, primaryTitle, originalTitle, isAdult, startYear, endYear, runtimeMinutes, genres)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      record.tconst,
      record.titleType,
      record.primaryTitle,
      record.originalTitle,
      record.isAdult,
      record.startYear,
      record.endYear,
      record.runtimeMinutes,
      record.genres
    ]
  );
}

export function upsertName(record: NameRecord) {
  db.query(
    `INSERT OR REPLACE INTO names
     (nconst, primaryName, birthYear, deathYear, primaryProfession, knownForTitles)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [
      record.nconst,
      record.primaryName,
      record.birthYear,
      record.deathYear,
      record.primaryProfession,
      record.knownForTitles
    ]
  );
}

export function upsertRating(record: RatingRecord) {
  db.query(
    `INSERT OR REPLACE INTO title_ratings (tconst, averageRating, numVotes)
     VALUES (?, ?, ?)`,
    [record.tconst, record.averageRating, record.numVotes]
  );
}

export function upsertPrincipal(record: PrincipalRecord) {
  db.query(
    `INSERT INTO title_principals (tconst, ordering, nconst, category, job, characters)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [record.tconst, record.ordering, record.nconst, record.category, record.job, record.characters]
  );
}

export function upsertAka(record: AkaRecord) {
  db.query(
    `INSERT INTO title_akas (titleId, ordering, title, region, language, types, attributes, isOriginalTitle)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      record.titleId,
      record.ordering,
      record.title,
      record.region,
      record.language,
      record.types,
      record.attributes,
      record.isOriginalTitle
    ]
  );
}

export function upsertCrew(record: CrewRecord) {
  db.query(
    `INSERT OR REPLACE INTO title_crew (tconst, directors, writers) VALUES (?, ?, ?)`,
    [record.tconst, record.directors, record.writers]
  );
}

export function upsertEpisode(record: EpisodeRecord) {
  db.query(
    `INSERT OR REPLACE INTO title_episodes (tconst, parentTconst, seasonNumber, episodeNumber)
     VALUES (?, ?, ?, ?)`,
    [record.tconst, record.parentTconst, record.seasonNumber, record.episodeNumber]
  );
}

export type QueryRow = Record<string, unknown>;

export function rowToObject(row: unknown[]): QueryRow {
  const out: QueryRow = {};
  for (let index = 0; index < row.length; index++) {
    out[String(index)] = row[index];
  }
  return out;
}

