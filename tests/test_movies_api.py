from __future__ import annotations

import importlib

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.database import get_session_factory, recreate_schema
from app.models import Movie, MovieGenre, MovieRating


def test_movies_list_uses_default_filters_and_omits_total_by_default(tmp_path, monkeypatch):
    db_path = tmp_path / "movies.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    app_main = importlib.import_module("app.main")
    app_main = importlib.reload(app_main)

    engine = create_engine(f"sqlite:///{db_path}")
    recreate_schema(engine, drop_existing=False)
    app_main.engine = engine
    app_main.session_factory = get_session_factory(engine)

    with app_main.session_factory() as session:
        session.add_all(
            [
                Movie(
                    id="tt0000001",
                    title_type="movie",
                    primary_title="Alpha",
                    original_title="Alpha",
                    genres_text="Drama,Thriller",
                    is_adult=False,
                    start_year=2024,
                ),
                MovieRating(movie_id="tt0000001", average_rating=8.5, num_votes=150),
                MovieGenre(movie_id="tt0000001", genre="Drama"),
                MovieGenre(movie_id="tt0000001", genre="Thriller"),
                Movie(
                    id="tt0000002",
                    title_type="tvSeries",
                    primary_title="Beta",
                    original_title="Beta",
                    genres_text="Drama",
                    is_adult=False,
                    start_year=2024,
                ),
                MovieRating(movie_id="tt0000002", average_rating=9.0, num_votes=500),
                MovieGenre(movie_id="tt0000002", genre="Drama"),
                Movie(
                    id="tt0000003",
                    title_type="movie",
                    primary_title="Gamma",
                    original_title="Gamma",
                    genres_text="Comedy",
                    is_adult=False,
                    start_year=2024,
                ),
                MovieRating(movie_id="tt0000003", average_rating=9.7, num_votes=50),
                MovieGenre(movie_id="tt0000003", genre="Comedy"),
            ]
        )
        session.commit()

    client = TestClient(app_main.app)

    response = client.get("/movies")
    assert response.status_code == 200
    payload = response.json()

    assert [item["id"] for item in payload["data"]] == ["tt0000001"]
    assert payload["data"][0]["genres"] == ["Drama", "Thriller"]
    assert payload["meta"]["page"] == 1
    assert payload["meta"]["pageSize"] == 25
    assert payload["meta"]["hasNext"] is False
    assert "total" not in payload["meta"]
    assert "totalPages" not in payload["meta"]

    response = client.get("/movies?includeTotal=true")
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["meta"]["totalPages"] == 1
    assert payload["meta"]["hasNext"] is False


def test_recommendations_keep_total_pagination_metadata(tmp_path, monkeypatch):
    db_path = tmp_path / "movies.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    app_main = importlib.import_module("app.main")
    app_main = importlib.reload(app_main)

    engine = create_engine(f"sqlite:///{db_path}")
    recreate_schema(engine, drop_existing=False)
    app_main.engine = engine
    app_main.session_factory = get_session_factory(engine)

    with app_main.session_factory() as session:
        session.add_all(
            [
                Movie(
                    id="tt1000001",
                    title_type="movie",
                    primary_title="Selected",
                    original_title="Selected",
                    genres_text="Drama",
                    is_adult=False,
                ),
                MovieGenre(movie_id="tt1000001", genre="Drama"),
                Movie(
                    id="tt1000002",
                    title_type="movie",
                    primary_title="Candidate A",
                    original_title="Candidate A",
                    genres_text="Drama",
                    is_adult=False,
                ),
                MovieRating(movie_id="tt1000002", average_rating=8.5, num_votes=200),
                MovieGenre(movie_id="tt1000002", genre="Drama"),
                Movie(
                    id="tt1000003",
                    title_type="movie",
                    primary_title="Candidate B",
                    original_title="Candidate B",
                    genres_text="Drama",
                    is_adult=False,
                ),
                MovieRating(movie_id="tt1000003", average_rating=8.0, num_votes=100),
                MovieGenre(movie_id="tt1000003", genre="Drama"),
            ]
        )
        session.commit()

    client = TestClient(app_main.app)
    response = client.post(
        "/recommendations",
        json={"selectedMovieIds": ["tt1000001"], "page": 1, "pageSize": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["meta"]["hasNext"] is True
    assert payload["meta"]["total"] == 2
    assert payload["meta"]["totalPages"] == 2
