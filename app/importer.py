from __future__ import annotations

import gzip
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, insert, text
from sqlalchemy.orm import Session

from app.database import create_indexes, drop_indexes, get_engine, get_session_factory, recreate_schema
from app.models import (
    Movie,
    MovieAka,
    MovieCrewLink,
    MovieEpisode,
    MovieGenre,
    MoviePrincipal,
    MovieRating,
    Person,
    PersonKnownForTitle,
    PersonProfession,
)


def is_null(value: str | None) -> bool:
    return value is None or value == "" or value == "\\N"


def parse_int(value: str | None) -> int | None:
    if is_null(value):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    if is_null(value):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except ValueError:
        return None


def parse_bool(value: str | None) -> bool:
    return value == "1"


def split_list(value: str | None) -> list[str]:
    if is_null(value):
        return []
    return [part for part in value.split(",") if part and part != "\\N"]


def log_progress(label: str, count: int, every: int = 100_000) -> None:
    if count and count % every == 0:
        print(f"{label}: processed {count}", flush=True)


def iter_tsv_gz(path: Path) -> Iterator[list[str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        header = True
        for line in handle:
            if header:
                header = False
                continue
            line = line.rstrip("\n")
            if not line:
                continue
            yield line.split("\t")


def flush_insert(session: Session, model, batch: list[dict[str, object]]) -> None:  # type: ignore[no-untyped-def]
    if batch:
        session.execute(insert(model), batch)


def drop_database_file(engine: Engine) -> None:
    if engine.url.get_backend_name() != "sqlite":
        return
    db_path = engine.url.database
    if not db_path:
        return
    path = Path(db_path)
    if path.exists():
        path.unlink()


def import_movies(session: Session, path: Path) -> None:
    movie_rows: list[dict[str, object]] = []
    count = 0
    for parts in iter_tsv_gz(path):
        count += 1
        movie_rows.append(
            {
                "id": parts[0],
                "title_type": parts[1],
                "primary_title": parts[2],
                "original_title": parts[3],
                "is_adult": parse_bool(parts[4]),
                "start_year": parse_int(parts[5]),
                "end_year": parse_int(parts[6]),
                "runtime_minutes": parse_int(parts[7]),
            }
        )
        if len(movie_rows) >= 5000:
            flush_insert(session, Movie, movie_rows)
            movie_rows = []
        log_progress(path.name, count)

    flush_insert(session, Movie, movie_rows)


def import_movie_genres(session: Session, path: Path) -> None:
    genre_rows: list[dict[str, object]] = []
    count = 0
    for parts in iter_tsv_gz(path):
        count += 1
        for genre in split_list(parts[8]):
            genre_rows.append({"movie_id": parts[0], "genre": genre})
        if len(genre_rows) >= 5000:
            flush_insert(session, MovieGenre, genre_rows)
            genre_rows = []
        log_progress(f"{path.name} genres", count)

    flush_insert(session, MovieGenre, genre_rows)


def import_people(session: Session, path: Path) -> None:
    people_rows: list[dict[str, object]] = []
    count = 0

    for parts in iter_tsv_gz(path):
        count += 1
        person_id = parts[0]
        people_rows.append(
            {
                "id": person_id,
                "primary_name": parts[1],
                "birth_year": parse_int(parts[2]),
                "death_year": parse_int(parts[3]),
            }
        )
        if len(people_rows) >= 5000:
            flush_insert(session, Person, people_rows)
            people_rows = []
        log_progress(path.name, count)

    flush_insert(session, Person, people_rows)


def import_people_metadata(session: Session, path: Path) -> None:
    profession_rows: list[dict[str, object]] = []
    known_for_rows: list[dict[str, object]] = []
    count = 0

    for parts in iter_tsv_gz(path):
        count += 1
        person_id = parts[0]
        for profession in split_list(parts[4]):
            profession_rows.append({"person_id": person_id, "profession": profession})
        for position, movie_id in enumerate(split_list(parts[5])):
            known_for_rows.append({"person_id": person_id, "movie_id": movie_id, "position": position})
        if len(profession_rows) >= 5000:
            flush_insert(session, PersonProfession, profession_rows)
            profession_rows = []
        if len(known_for_rows) >= 5000:
            flush_insert(session, PersonKnownForTitle, known_for_rows)
            known_for_rows = []
        log_progress(f"{path.name} metadata", count)

    flush_insert(session, PersonProfession, profession_rows)
    flush_insert(session, PersonKnownForTitle, known_for_rows)


def import_ratings(session: Session, path: Path) -> None:
    rows: list[dict[str, object]] = []
    count = 0
    for parts in iter_tsv_gz(path):
        count += 1
        rows.append({"movie_id": parts[0], "average_rating": parse_float(parts[1]) or 0.0, "num_votes": parse_int(parts[2]) or 0})
        if len(rows) >= 5000:
            flush_insert(session, MovieRating, rows)
            rows = []
        log_progress(path.name, count)
    flush_insert(session, MovieRating, rows)


def import_principals(session: Session, path: Path) -> None:
    rows: list[dict[str, object]] = []
    count = 0
    for parts in iter_tsv_gz(path):
        count += 1
        rows.append(
            {
                "movie_id": parts[0],
                "ordering": parse_int(parts[1]) or 0,
                "person_id": parts[2],
                "category": None if is_null(parts[3]) else parts[3],
                "job": None if is_null(parts[4]) else parts[4],
                "characters": None if is_null(parts[5]) else parts[5],
            }
        )
        if len(rows) >= 5000:
            flush_insert(session, MoviePrincipal, rows)
            rows = []
        log_progress(path.name, count)
    flush_insert(session, MoviePrincipal, rows)


def import_akas(session: Session, path: Path) -> None:
    rows: list[dict[str, object]] = []
    count = 0
    for parts in iter_tsv_gz(path):
        count += 1
        rows.append(
            {
                "movie_id": parts[0],
                "ordering": parse_int(parts[1]) or 0,
                "title": parts[2],
                "region": None if is_null(parts[3]) else parts[3],
                "language": None if is_null(parts[4]) else parts[4],
                "types": None if is_null(parts[5]) else parts[5],
                "attributes": None if is_null(parts[6]) else parts[6],
                "is_original_title": parse_bool(parts[7]),
            }
        )
        if len(rows) >= 5000:
            flush_insert(session, MovieAka, rows)
            rows = []
        log_progress(path.name, count)
    flush_insert(session, MovieAka, rows)


def import_crew(session: Session, path: Path) -> None:
    rows: list[dict[str, object]] = []
    count = 0
    for parts in iter_tsv_gz(path):
        count += 1
        movie_id = parts[0]
        for role, members in (("director", parts[1]), ("writer", parts[2])):
            for person_id in split_list(members):
                rows.append({"movie_id": movie_id, "person_id": person_id, "role": role})
                if len(rows) >= 5000:
                    flush_insert(session, MovieCrewLink, rows)
                    rows = []
        log_progress(path.name, count)
    flush_insert(session, MovieCrewLink, rows)


def import_episodes(session: Session, path: Path) -> None:
    rows: list[dict[str, object]] = []
    count = 0
    for parts in iter_tsv_gz(path):
        count += 1
        rows.append(
            {
                "movie_id": parts[0],
                "parent_movie_id": parts[1],
                "season_number": parse_int(parts[2]),
                "episode_number": parse_int(parts[3]),
            }
        )
        if len(rows) >= 5000:
            flush_insert(session, MovieEpisode, rows)
            rows = []
        log_progress(path.name, count)
    flush_insert(session, MovieEpisode, rows)


def import_imdb_data(
    database_url: str,
    data_dir: Path,
    reset: bool = True,
) -> None:
    engine = get_engine(database_url)
    if reset:
        drop_database_file(engine)
    recreate_schema(engine, drop_existing=True)
    drop_indexes(engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        session.execute(text("PRAGMA foreign_keys = OFF"))
        session.execute(text("PRAGMA synchronous = OFF"))
        session.execute(text("PRAGMA journal_mode = MEMORY"))

        import_movies(session, data_dir / "title.basics.tsv.gz")
        import_movie_genres(session, data_dir / "title.basics.tsv.gz")
        import_people(session, data_dir / "name.basics.tsv.gz")
        import_people_metadata(session, data_dir / "name.basics.tsv.gz")
        import_ratings(session, data_dir / "title.ratings.tsv.gz")
        import_principals(session, data_dir / "title.principals.tsv.gz")
        import_akas(session, data_dir / "title.akas.tsv.gz")
        import_crew(session, data_dir / "title.crew.tsv.gz")
        import_episodes(session, data_dir / "title.episode.tsv.gz")
        session.commit()

    create_indexes(engine)
