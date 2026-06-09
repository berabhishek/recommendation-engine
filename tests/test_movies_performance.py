from __future__ import annotations

import importlib
import statistics
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.database import get_session_factory, recreate_schema
from app.models import Movie, MovieGenre, MovieRating


pytestmark = pytest.mark.performance


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean_ms": statistics.fmean(values),
        "median_ms": statistics.median(values),
        "p95_ms": _percentile(values, 0.95),
    }


def _seed_movies(session, total_movies: int = 4000) -> None:
    movies: list[dict[str, object]] = []
    ratings: list[dict[str, object]] = []
    genres: list[dict[str, object]] = []

    for idx in range(total_movies):
        movie_id = f"tt{idx:07d}"
        is_movie = idx % 2 == 0
        vote_count = 100 + (idx % 500)
        movies.append(
            {
                "id": movie_id,
                "title_type": "movie" if is_movie else "tvSeries",
                "primary_title": f"Title {idx:04d}",
                "original_title": f"Title {idx:04d}",
                "genres_text": "Drama,Thriller" if is_movie else "Comedy",
                "is_adult": False,
                "start_year": 1990 + (idx % 30),
                "end_year": None,
                "runtime_minutes": 80 + (idx % 60),
            }
        )
        ratings.append(
            {
                "movie_id": movie_id,
                "average_rating": 5.0 + (idx % 50) / 10.0,
                "num_votes": vote_count,
            }
        )
        genres.append({"movie_id": movie_id, "genre": "Drama" if is_movie else "Comedy"})
        if is_movie:
            genres.append({"movie_id": movie_id, "genre": "Thriller"})

    session.execute(Movie.__table__.insert(), movies)
    session.execute(MovieRating.__table__.insert(), ratings)
    session.execute(MovieGenre.__table__.insert(), genres)
    session.commit()


def test_movies_list_performance_benchmark(tmp_path, monkeypatch):
    db_path = tmp_path / "movies-perf.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    app_main = importlib.import_module("app.main")
    app_main = importlib.reload(app_main)

    engine = create_engine(f"sqlite:///{db_path}")
    recreate_schema(engine, drop_existing=False)
    app_main.engine = engine
    app_main.session_factory = get_session_factory(engine)

    with app_main.session_factory() as session:
        _seed_movies(session)

    client = TestClient(app_main.app)

    warmup_requests = 5
    measured_requests = 25

    for _ in range(warmup_requests):
        assert client.get("/movies?page=1&pageSize=25").status_code == 200
        assert client.get("/movies?page=1&pageSize=25&includeTotal=true").status_code == 200

    default_durations: list[float] = []
    counted_durations: list[float] = []

    for _ in range(measured_requests):
        start = time.perf_counter()
        response = client.get("/movies?page=1&pageSize=25")
        default_durations.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 200
        assert response.json()["meta"]["hasNext"] is True
        assert "total" not in response.json()["meta"]

        start = time.perf_counter()
        response = client.get("/movies?page=1&pageSize=25&includeTotal=true")
        counted_durations.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 2000
        assert response.json()["meta"]["hasNext"] is True

    default_stats = _summarize(default_durations)
    counted_stats = _summarize(counted_durations)

    print(
        "movies_list_default_ms "
        f"mean={default_stats['mean_ms']:.2f} "
        f"median={default_stats['median_ms']:.2f} "
        f"p95={default_stats['p95_ms']:.2f}"
    )
    print(
        "movies_list_include_total_ms "
        f"mean={counted_stats['mean_ms']:.2f} "
        f"median={counted_stats['median_ms']:.2f} "
        f"p95={counted_stats['p95_ms']:.2f}"
    )
