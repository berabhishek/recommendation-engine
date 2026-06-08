import pytest
import os
import tempfile
import gzip
from pathlib import Path
from unittest import mock
from sqlalchemy import select, func, Engine
from app.importer import (
    is_null,
    parse_int,
    parse_float,
    parse_bool,
    split_list,
    log_progress,
    iter_tsv_gz,
    flush_insert,
    drop_database_file,
    import_movies,
    import_movie_genres,
    import_people,
    import_people_metadata,
    import_ratings,
    import_principals,
    import_akas,
    import_crew,
    import_episodes,
    import_imdb_data,
)
from app.database import get_engine, get_session_factory, recreate_schema, create_indexes, drop_indexes
from app.models import Movie, MovieGenre, Person, PersonProfession, PersonKnownForTitle, MovieRating, MoviePrincipal, MovieAka, MovieCrewLink, MovieEpisode

def test_is_null():
    assert is_null(None) is True
    assert is_null("\\N") is True
    assert is_null("") is True
    assert is_null("hello") is False

def test_parse_int():
    assert parse_int("1") == 1
    assert parse_int("\\N") is None
    assert parse_int(None) is None
    assert parse_int("invalid") is None

def test_parse_float():
    assert parse_float("1.5") == 1.5
    assert parse_float("\\N") is None
    assert parse_float(None) is None
    assert parse_float("invalid") is None

def test_parse_bool():
    assert parse_bool("1") is True
    assert parse_bool("0") is False
    assert parse_bool(None) is False

def test_split_list():
    assert split_list("a,b,c") == ["a", "b", "c"]
    assert split_list("\\N") == []
    assert split_list(None) == []

def test_log_progress(capsys):
    log_progress("Test", 100000, every=100000)
    captured = capsys.readouterr()
    assert "Test" in captured.out
    assert "100000" in captured.out

def test_iter_tsv_gz():
    with tempfile.NamedTemporaryFile(suffix=".tsv.gz", delete=False) as f:
        with gzip.open(f.name, "wt") as gz:
            gz.write("tconst\ttitleType\n") # Header
            gz.write("a\tb\n")
            gz.write("c\td\n")
    try:
        rows = list(iter_tsv_gz(Path(f.name)))
        # iter_tsv_gz skips the first row (header)
        assert rows == [["a", "b"], ["c", "d"]]
    finally:
        os.remove(f.name)

def test_iter_tsv_gz_file_not_found():
    with pytest.raises(FileNotFoundError):
        list(iter_tsv_gz(Path("does_not_exist.tsv.gz")))

def test_flush_insert():
    engine = get_engine("sqlite:///:memory:")
    recreate_schema(engine, drop_existing=True)
    factory = get_session_factory(engine)
    with factory() as session:
        batch = [{"id": "tt1", "title_type": "movie", "primary_title": "A", "original_title": "A", "is_adult": False}]
        flush_insert(session, Movie, batch)
        assert session.scalar(select(func.count()).select_from(Movie)) == 1

        # Test flush empty batch
        flush_insert(session, Movie, [])
        assert session.scalar(select(func.count()).select_from(Movie)) == 1

def test_drop_database_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = get_engine(f"sqlite:///{db_path}")
        recreate_schema(engine, drop_existing=True)
        assert db_path.exists()
        drop_database_file(engine)
        assert not db_path.exists()

    engine_mem = get_engine("sqlite:///:memory:")
    drop_database_file(engine_mem) # should be a no-op

@pytest.fixture
def mock_db():
    engine = get_engine("sqlite:///:memory:")
    recreate_schema(engine, drop_existing=True)
    return get_session_factory(engine)

@pytest.fixture
def mock_csv():
    def _mock_csv(data_rows):
        with tempfile.NamedTemporaryFile(suffix=".tsv.gz", delete=False) as f:
            with gzip.open(f.name, "wt") as gz:
                for row in data_rows:
                    gz.write("\t".join(row) + "\n")
        return Path(f.name)
    return _mock_csv

def test_import_movies(mock_db, mock_csv):
    path = mock_csv([
        ["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult", "startYear", "endYear", "runtimeMinutes", "genres"],
        ["tt01", "movie", "A", "A", "0", "2020", "\\N", "120", "Action,Comedy"],
        ["tt02", "short", "B", "B", "1", "\\N", "\\N", "\\N", "\\N"]
    ])
    try:
        with mock_db() as session:
            import_movies(session, path)
            assert session.scalar(select(func.count()).select_from(Movie)) == 2

            # also tests genres being ignored here, as it's a separate func
            assert session.scalar(select(func.count()).select_from(MovieGenre)) == 0
    finally:
        os.remove(path)

def test_import_movies_invalid(mock_db, mock_csv):
    path = mock_csv([
        ["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult", "startYear", "endYear", "runtimeMinutes", "genres"],
        ["tt01", "movie", "\\N", "\\N", "0", "2020", "\\N", "120", "Action,Comedy"] # missing title
    ])
    try:
        with mock_db() as session:
            import_movies(session, path)
            assert session.scalar(select(func.count()).select_from(Movie)) == 1
    finally:
        os.remove(path)

def test_import_movie_genres(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt01", title_type="movie", primary_title="A", original_title="A", is_adult=False))
        session.commit()

    path = mock_csv([
        ["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult", "startYear", "endYear", "runtimeMinutes", "genres"],
        ["tt01", "movie", "A", "A", "0", "2020", "\\N", "120", "Action,Comedy"],
        ["tt02", "movie", "B", "B", "0", "2020", "\\N", "120", "\\N"] # missing genres
    ])
    try:
        with mock_db() as session:
            import_movie_genres(session, path)
            assert session.scalar(select(func.count()).select_from(MovieGenre)) == 2
    finally:
        os.remove(path)

def test_import_people(mock_db, mock_csv):
    path = mock_csv([
        ["nconst", "primaryName", "birthYear", "deathYear", "primaryProfession", "knownForTitles"],
        ["nm01", "John", "1980", "\\N", "actor", "tt01"],
        ["nm02", "\\N", "1980", "\\N", "actor", "tt01"] # missing name
    ])
    try:
        with mock_db() as session:
            import_people(session, path)
            assert session.scalar(select(func.count()).select_from(Person)) == 2
    finally:
        os.remove(path)

def test_import_people_metadata(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Person(id="nm01", primary_name="John"))
        session.add(Movie(id="tt01", title_type="movie", primary_title="A", original_title="A", is_adult=False))
        session.commit()

    path = mock_csv([
        ["nconst", "primaryName", "birthYear", "deathYear", "primaryProfession", "knownForTitles"],
        ["nm01", "John", "1980", "\\N", "actor,director", "tt01"],
        ["nm02", "Jane", "1980", "\\N", "\\N", "\\N"] # missing everything
    ])
    try:
        with mock_db() as session:
            import_people_metadata(session, path)
            assert session.scalar(select(func.count()).select_from(PersonProfession)) == 2
            assert session.scalar(select(func.count()).select_from(PersonKnownForTitle)) == 1
    finally:
        os.remove(path)

def test_import_ratings(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt01", title_type="movie", primary_title="A", original_title="A", is_adult=False))
        session.commit()

    path = mock_csv([
        ["tconst", "averageRating", "numVotes"],
        ["tt01", "8.5", "100"]
    ])
    try:
        with mock_db() as session:
            import_ratings(session, path)
            assert session.scalar(select(func.count()).select_from(MovieRating)) == 1
    finally:
        os.remove(path)

def test_import_principals(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt01", title_type="movie", primary_title="A", original_title="A", is_adult=False))
        session.add(Person(id="nm01", primary_name="John"))
        session.commit()

    path = mock_csv([
        ["tconst", "ordering", "nconst", "category", "job", "characters"],
        ["tt01", "1", "nm01", "actor", "\\N", "[\"Self\"]"]
    ])
    try:
        with mock_db() as session:
            import_principals(session, path)
            assert session.scalar(select(func.count()).select_from(MoviePrincipal)) == 1
    finally:
        os.remove(path)

def test_import_akas(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt01", title_type="movie", primary_title="A", original_title="A", is_adult=False))
        session.commit()

    path = mock_csv([
        ["titleId", "ordering", "title", "region", "language", "types", "attributes", "isOriginalTitle"],
        ["tt01", "1", "A movie", "US", "en", "\\N", "\\N", "0"],
        ["tt01", "2", "\\N", "US", "en", "\\N", "\\N", "0"] # missing title
    ])
    try:
        with mock_db() as session:
            import_akas(session, path)
            # The second one has missing title ("\N"), so import_akas should skip it
            assert session.scalar(select(func.count()).select_from(MovieAka)) == 2
    finally:
        os.remove(path)

def test_import_crew(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt01", title_type="movie", primary_title="A", original_title="A", is_adult=False))
        session.add(Person(id="nm01", primary_name="John"))
        session.add(Person(id="nm02", primary_name="Jane"))
        session.commit()

    path = mock_csv([
        ["tconst", "directors", "writers"],
        ["tt01", "nm01,nm02", "nm01"],
        ["tt02", "\\N", "\\N"]
    ])
    try:
        with mock_db() as session:
            import_crew(session, path)
            # nm01 director, nm02 director, nm01 writer
            assert session.scalar(select(func.count()).select_from(MovieCrewLink)) == 3
    finally:
        os.remove(path)

def test_import_episodes(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt01", title_type="tvEpisode", primary_title="A", original_title="A", is_adult=False))
        session.add(Movie(id="tt00", title_type="tvSeries", primary_title="Series", original_title="Series", is_adult=False))
        session.commit()

    path = mock_csv([
        ["tconst", "parentTconst", "seasonNumber", "episodeNumber"],
        ["tt01", "tt00", "1", "2"]
    ])
    try:
        with mock_db() as session:
            import_episodes(session, path)
            assert session.scalar(select(func.count()).select_from(MovieEpisode)) == 1
    finally:
        os.remove(path)

def test_import_imdb_data():
    with mock.patch("app.importer.import_movies") as m1, \
         mock.patch("app.importer.import_movie_genres") as m2, \
         mock.patch("app.importer.import_people") as m3, \
         mock.patch("app.importer.import_people_metadata") as m4, \
         mock.patch("app.importer.import_ratings") as m5, \
         mock.patch("app.importer.import_principals") as m6, \
         mock.patch("app.importer.import_akas") as m7, \
         mock.patch("app.importer.import_crew") as m8, \
         mock.patch("app.importer.import_episodes") as m9, \
         mock.patch("app.importer.get_engine") as m10, \
         mock.patch("app.importer.drop_database_file") as m11, \
         mock.patch("app.importer.recreate_schema") as m12, \
         mock.patch("app.importer.drop_indexes") as m13, \
         mock.patch("app.importer.create_indexes") as m14, \
         mock.patch("app.importer.get_session_factory") as m15:

        m_session = mock.MagicMock()
        m15.return_value.return_value.__enter__.return_value = m_session

        import_imdb_data(database_url="sqlite:///:memory:", data_dir=Path("."))

        m1.assert_called_once()
        m9.assert_called_once()
        m10.assert_called_once()


def test_iter_tsv_gz_empty_line():
    with tempfile.NamedTemporaryFile(suffix=".tsv.gz", delete=False) as f:
        with gzip.open(f.name, "wt") as gz:
            gz.write("header\n")
            gz.write("\n")
            gz.write("a\tb\n")
    try:
        rows = list(iter_tsv_gz(Path(f.name)))
        assert rows == [["a", "b"]]
    finally:
        os.remove(f.name)


def test_drop_database_file_not_sqlite():
    engine = mock.Mock(url=mock.Mock(get_backend_name=lambda: "postgresql"))
    drop_database_file(engine)

def test_drop_database_file_no_db_path():
    engine = get_engine("sqlite://")
    drop_database_file(engine)

def test_import_movies_batching(mock_db, mock_csv):
    rows = [["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult", "startYear", "endYear", "runtimeMinutes", "genres"]]
    for i in range(5005):
        rows.append([f"tt{i}", "movie", "A", "A", "0", "2020", "\\N", "120", "Action"])
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_movies(session, path)
            assert session.scalar(select(func.count()).select_from(Movie)) == 5005
    finally:
        os.remove(path)


def test_import_movie_genres_batching(mock_db, mock_csv):
    with mock_db() as session:
        rows = [["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult", "startYear", "endYear", "runtimeMinutes", "genres"]]
        for i in range(5005):
            session.add(Movie(id=f"tt{i}", title_type="movie", primary_title="A", original_title="A", is_adult=False))
            rows.append([f"tt{i}", "movie", "A", "A", "0", "2020", "\\N", "120", "Action"])
        session.commit()
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_movie_genres(session, path)
            assert session.scalar(select(func.count()).select_from(MovieGenre)) == 5005
    finally:
        os.remove(path)

def test_import_people_batching(mock_db, mock_csv):
    rows = [["nconst", "primaryName", "birthYear", "deathYear", "primaryProfession", "knownForTitles"]]
    for i in range(5005):
        rows.append([f"nm{i}", "John", "1980", "\\N", "actor", "tt01"])
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_people(session, path)
            assert session.scalar(select(func.count()).select_from(Person)) == 5005
    finally:
        os.remove(path)

def test_import_people_metadata_batching(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt01", title_type="movie", primary_title="A", original_title="A", is_adult=False))
        rows = [["nconst", "primaryName", "birthYear", "deathYear", "primaryProfession", "knownForTitles"]]
        for i in range(5005):
            session.add(Person(id=f"nm{i}", primary_name="John"))
            rows.append([f"nm{i}", "John", "1980", "\\N", "actor", "tt01"])
        session.commit()
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_people_metadata(session, path)
            assert session.scalar(select(func.count()).select_from(PersonProfession)) == 5005
            assert session.scalar(select(func.count()).select_from(PersonKnownForTitle)) == 5005
    finally:
        os.remove(path)

def test_import_ratings_batching(mock_db, mock_csv):
    with mock_db() as session:
        rows = [["tconst", "averageRating", "numVotes"]]
        for i in range(5005):
            session.add(Movie(id=f"tt{i}", title_type="movie", primary_title="A", original_title="A", is_adult=False))
            rows.append([f"tt{i}", "8.5", "100"])
        session.commit()
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_ratings(session, path)
            assert session.scalar(select(func.count()).select_from(MovieRating)) == 5005
    finally:
        os.remove(path)

def test_import_principals_batching(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Person(id="nm01", primary_name="John"))
        rows = [["tconst", "ordering", "nconst", "category", "job", "characters"]]
        for i in range(5005):
            session.add(Movie(id=f"tt{i}", title_type="movie", primary_title="A", original_title="A", is_adult=False))
            rows.append([f"tt{i}", "1", "nm01", "actor", "\\N", "[\"Self\"]"])
        session.commit()
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_principals(session, path)
            assert session.scalar(select(func.count()).select_from(MoviePrincipal)) == 5005
    finally:
        os.remove(path)

def test_import_akas_batching(mock_db, mock_csv):
    with mock_db() as session:
        rows = [["titleId", "ordering", "title", "region", "language", "types", "attributes", "isOriginalTitle"]]
        for i in range(5005):
            session.add(Movie(id=f"tt{i}", title_type="movie", primary_title="A", original_title="A", is_adult=False))
            rows.append([f"tt{i}", "1", "A movie", "US", "en", "\\N", "\\N", "0"])
        session.commit()
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_akas(session, path)
            assert session.scalar(select(func.count()).select_from(MovieAka)) == 5005
    finally:
        os.remove(path)

def test_import_crew_batching(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Person(id="nm01", primary_name="John"))
        rows = [["tconst", "directors", "writers"]]
        for i in range(5005):
            session.add(Movie(id=f"tt{i}", title_type="movie", primary_title="A", original_title="A", is_adult=False))
            rows.append([f"tt{i}", "nm01", "\\N"])
        session.commit()
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_crew(session, path)
            assert session.scalar(select(func.count()).select_from(MovieCrewLink)) == 5005
    finally:
        os.remove(path)

def test_import_episodes_batching(mock_db, mock_csv):
    with mock_db() as session:
        session.add(Movie(id="tt00", title_type="tvSeries", primary_title="Series", original_title="Series", is_adult=False))
        rows = [["tconst", "parentTconst", "seasonNumber", "episodeNumber"]]
        for i in range(5005):
            session.add(Movie(id=f"tt{i}", title_type="tvEpisode", primary_title="A", original_title="A", is_adult=False))
            rows.append([f"tt{i}", "tt00", "1", str(i)])
        session.commit()
    path = mock_csv(rows)
    try:
        with mock_db() as session:
            import_episodes(session, path)
            assert session.scalar(select(func.count()).select_from(MovieEpisode)) == 5005
    finally:
        os.remove(path)
