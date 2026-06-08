import { createReadStream } from "node:fs";
import { createGunzip } from "node:zlib";
import readline from "node:readline";
import {
  db,
  initDB,
  mapAka,
  mapCrew,
  mapEpisode,
  mapName,
  mapPrincipal,
  mapRating,
  mapTitle,
  upsertAka,
  upsertCrew,
  upsertEpisode,
  upsertName,
  upsertPrincipal,
  upsertRating,
  upsertTitle
} from "../db.ts";

initDB();

async function importTsvGz(filePath: string, handler: (parts: string[]) => void) {
  const stream = createReadStream(filePath).pipe(createGunzip());
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  let first = true;
  let count = 0;
  for await (const line of rl) {
    if (first) {
      first = false;
      continue;
    }
    if (!line) continue;
    handler(line.split("\t"));
    count++;
    if (count % 100000 === 0) console.log(`${filePath}: ${count}`);
  }
  console.log(`${filePath}: imported ${count}`);
}

async function main() {
  db.query("BEGIN");
  try {
    await importTsvGz("raw data/title.basics.tsv.gz", (parts) => upsertTitle(mapTitle(parts)));
    await importTsvGz("raw data/name.basics.tsv.gz", (parts) => upsertName(mapName(parts)));
    await importTsvGz("raw data/title.ratings.tsv.gz", (parts) => upsertRating(mapRating(parts)));
    await importTsvGz("raw data/title.principals.tsv.gz", (parts) => upsertPrincipal(mapPrincipal(parts)));
    await importTsvGz("raw data/title.akas.tsv.gz", (parts) => upsertAka(mapAka(parts)));
    await importTsvGz("raw data/title.crew.tsv.gz", (parts) => upsertCrew(mapCrew(parts)));
    await importTsvGz("raw data/title.episode.tsv.gz", (parts) => upsertEpisode(mapEpisode(parts)));
    db.query("COMMIT");
  } catch (error) {
    db.query("ROLLBACK");
    throw error;
  }
}

if (import.meta.main) {
  main().catch((error) => {
    console.error(error);
    Deno.exit(1);
  });
}
