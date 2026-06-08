import pytest
from unittest import mock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, db_session, split_csv, get_page, get_page_size, pagination_meta
from app.database import Base
from app.models import Movie, MovieGenre, MovieRating, Person, MoviePrincipal, MovieAka, MovieCrewLink, MovieEpisode

# Use an on-disk database for testing so the separate threads/connections see the same data
SQLALCHEMY_DATABASE_URL = "sqlite:///file:memdb1?mode=memory&cache=shared"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[db_session] = override_db_session

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Populate test data
    m1 = Movie(id="tt01", title_type="movie", primary_title="The Matrix", original_title="The Matrix", is_adult=False, start_year=1999, runtime_minutes=136)
    m2 = Movie(id="tt02", title_type="movie", primary_title="The Matrix Reloaded", original_title="The Matrix Reloaded", is_adult=False, start_year=2003, runtime_minutes=138)
    m3 = Movie(id="tt03", title_type="tvSeries", primary_title="Dark", original_title="Dark", is_adult=False, start_year=2017, runtime_minutes=60)

    db.add_all([m1, m2, m3])
    db.commit()

    g1 = MovieGenre(movie_id="tt01", genre="Action")
    g2 = MovieGenre(movie_id="tt01", genre="Sci-Fi")
    g3 = MovieGenre(movie_id="tt02", genre="Action")
    g4 = MovieGenre(movie_id="tt03", genre="Thriller")
    db.add_all([g1, g2, g3, g4])
    db.commit()

    r1 = MovieRating(movie_id="tt01", average_rating=8.7, num_votes=150000)
    r2 = MovieRating(movie_id="tt02", average_rating=7.2, num_votes=100000)
    r3 = MovieRating(movie_id="tt03", average_rating=8.8, num_votes=50000)
    db.add_all([r1, r2, r3])
    db.commit()

    p1 = Person(id="nm01", primary_name="Keanu Reeves")
    p2 = Person(id="nm02", primary_name="Lana Wachowski")
    db.add_all([p1, p2])
    db.commit()

    mp1 = MoviePrincipal(movie_id="tt01", ordering=1, person_id="nm01", category="actor", characters="[\"Neo\"]")
    db.add(mp1)
    db.commit()

    aka1 = MovieAka(movie_id="tt01", ordering=1, title="Matrix", region="US", language="en", is_original_title=False)
    db.add(aka1)
    db.commit()

    crew1 = MovieCrewLink(movie_id="tt01", person_id="nm02", role="director")
    db.add(crew1)
    db.commit()

    ep1 = MovieEpisode(movie_id="tt03", parent_movie_id="tt00", season_number=1, episode_number=1)
    db.add(ep1)
    db.commit()

    db.close()
    yield

def test_split_csv():
    assert split_csv("a,b, c") == ["a", "b", "c"]
    assert split_csv(None) == []
    assert split_csv("") == []

def test_get_page():
    assert get_page(0) == 1
    assert get_page(5) == 5

def test_get_page_size():
    from app.settings import MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE
    assert get_page_size(10) == 10
    assert get_page_size(0) == DEFAULT_PAGE_SIZE
    assert get_page_size(MAX_PAGE_SIZE + 10) == MAX_PAGE_SIZE

def test_pagination_meta():
    meta = pagination_meta(1, 10, 25)
    assert meta.page == 1
    assert meta.page_size == 10
    assert meta.total == 25
    assert meta.total_pages == 3

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_startup_event():
    with TestClient(app) as local_client:
        response = local_client.get("/health")
        assert response.status_code == 200

def test_list_movies():
    response = client.get("/movies")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3
    assert data["meta"]["total"] == 3

    # Check default sort is rating desc
    assert data["data"][0]["id"] == "tt03" # Dark 8.8
    assert data["data"][1]["id"] == "tt01" # Matrix 8.7

def test_list_movies_sort():
    response = client.get("/movies?sortBy=title&sortDir=asc")
    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["id"] == "tt03" # Dark
    assert data["data"][1]["id"] == "tt01" # The Matrix

    response = client.get("/movies?sortBy=year&sortDir=asc")
    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["id"] == "tt01" # 1999

def test_list_movies_filter_query():
    response = client.get("/movies?q=Matrix")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert "Matrix" in data["data"][0]["primaryTitle"]

def test_list_movies_filter_title_type():
    response = client.get("/movies?titleType=tvSeries")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "tt03"

def test_list_movies_filter_genres():
    response = client.get("/movies?genres=Action")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2

    response = client.get("/movies?genres=Sci-Fi")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1

def test_list_movies_filter_year():
    response = client.get("/movies?yearMin=2000&yearMax=2010")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "tt02"

def test_list_movies_filter_rating_votes():
    response = client.get("/movies?minRating=8.0&minVotes=100000")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "tt01"

def test_get_movie():
    response = client.get("/movies/tt01")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "tt01"
    assert data["primaryTitle"] == "The Matrix"
    assert "Action" in data["genres"]
    assert "Sci-Fi" in data["genres"]
    assert data["akas"][0]["title"] == "Matrix"
    assert data["principals"][0]["person_id"] == "nm01"
    assert data["crewLinks"][0]["person_id"] == "nm02"
    assert data["episode"] is None

def test_get_movie_not_found():
    response = client.get("/movies/tt99")
    assert response.status_code == 404

def test_get_movie_with_episode():
    response = client.get("/movies/tt03")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "tt03"
    assert data["episode"]["season_number"] == 1

def test_recommend_movies_empty():
    response = client.post("/recommendations", json={"selectedMovieIds": []})
    assert response.status_code == 422 # FastAPI validation catches empty list due to min_length=1

def test_recommend_movies_not_found():
    response = client.post("/recommendations", json={"selectedMovieIds": ["tt99"]})
    assert response.status_code == 404

def test_recommend_movies():
    response = client.post("/recommendations", json={"selectedMovieIds": ["tt01"]})
    assert response.status_code == 200
    data = response.json()
    # It should recommend tt02 (Action genre match)
    assert len(data["data"]) > 0
    assert data["data"][0]["id"] == "tt02"
    assert data["data"][0]["sharedGenres"] == 1

def test_main():
    with mock.patch("uvicorn.run") as mock_run:
        from app.main import main
        main()
        mock_run.assert_called_once()


def test_db_session():
    from app.main import db_session
    # Need to test db_session generator directly
    gen = db_session()
    with mock.patch("app.main.session_factory") as mock_factory:
        mock_factory.return_value.__enter__.return_value = "mock_session"
        assert next(gen) == "mock_session"

def test_recommend_movies_db_logic():
    # Since we can't easily trigger the candidate loop branches without the right data,
    # let's add a test to cover those specific branches explicitly by requesting recommendations
    # for a movie that doesn't have overlapping genres or people to see the score logic trigger.
    response = client.post("/recommendations", json={"selectedMovieIds": ["tt03"]})
    assert response.status_code == 200


def test_recommendation_empty_selected():
    response = client.post("/recommendations", json={"selectedMovieIds": []})
    assert response.status_code == 422 # Because of Pydantic validation

    # We also want to hit line 269 directly without Pydantic:
    from app.main import recommend_movies
    from app.schemas import RecommendationRequest
    from fastapi import HTTPException

    # Bypass validation by instantiating manually or mocking
    req = mock.Mock()
    req.selected_movie_ids = []
    with pytest.raises(HTTPException) as excinfo:
        recommend_movies(req, session=mock.Mock())
    assert excinfo.value.status_code == 400


def test_recommendation_candidates_principals_and_crew():
    from app.main import recommend_movies
    db = TestingSessionLocal()
    # Create candidate with principals and crew
    # Make sure we recommend starting from tt01

    # We already have tt02 as a candidate, let's add principals and crew to tt02
    p3 = Person(id="nm03", primary_name="Someone")
    db.add(p3)
    db.commit()

    mp2 = MoviePrincipal(movie_id="tt02", ordering=1, person_id="nm03", category="actor")
    db.add(mp2)
    db.commit()

    crew2 = MovieCrewLink(movie_id="tt02", person_id="nm03", role="writer")
    db.add(crew2)
    db.commit()
    db.close()

    response = client.post("/recommendations", json={"selectedMovieIds": ["tt01"]})
    assert response.status_code == 200




def test_if_name_main():
    import runpy
    import sys
    with mock.patch.object(sys, "argv", ["app/main.py"]), mock.patch("uvicorn.run") as mock_run:
        runpy.run_module("app.main", run_name="__main__")
        mock_run.assert_called_once()
