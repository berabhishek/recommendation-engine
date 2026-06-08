import pytest
from app.schemas import (
    PaginationMeta,
    MovieSummary,
    MovieDetail,
    MovieListResponse,
    RecommendationRequest,
    RecommendationItem,
    RecommendationResponse,
)

def test_pagination_meta():
    meta = PaginationMeta(page=1, pageSize=20, total=100, totalPages=5)
    assert meta.page == 1
    assert meta.page_size == 20
    assert meta.total == 100
    assert meta.total_pages == 5

def test_movie_summary():
    summary = MovieSummary(
        id="tt0000001",
        titleType="short",
        primaryTitle="Carmencita",
        originalTitle="Carmencita",
        isAdult=False,
        startYear=1894,
        endYear=None,
        runtimeMinutes=1,
        genres=["Documentary", "Short"],
        averageRating=5.7,
        numVotes=1900,
    )
    assert summary.id == "tt0000001"
    assert summary.title_type == "short"
    assert summary.primary_title == "Carmencita"
    assert summary.original_title == "Carmencita"
    assert summary.is_adult is False
    assert summary.start_year == 1894
    assert summary.end_year is None
    assert summary.runtime_minutes == 1
    assert summary.genres == ["Documentary", "Short"]
    assert summary.average_rating == 5.7
    assert summary.num_votes == 1900

def test_movie_detail():
    detail = MovieDetail(
        id="tt0000001",
        titleType="short",
        primaryTitle="Carmencita",
        originalTitle="Carmencita",
        isAdult=False,
        startYear=1894,
        endYear=None,
        runtimeMinutes=1,
        genres=["Documentary", "Short"],
        averageRating=5.7,
        numVotes=1900,
        akas=[{"title": "Carmencita"}],
        principals=[{"person_id": "nm0000001"}],
        crewLinks=[{"person_id": "nm0000002"}],
        episode=None,
    )
    assert detail.akas == [{"title": "Carmencita"}]
    assert detail.principals == [{"person_id": "nm0000001"}]
    assert detail.crew_links == [{"person_id": "nm0000002"}]
    assert detail.episode is None

def test_movie_list_response():
    resp = MovieListResponse(
        data=[],
        meta=PaginationMeta(page=1, pageSize=20, total=0, totalPages=0)
    )
    assert resp.data == []
    assert resp.meta.page == 1

def test_recommendation_request():
    req = RecommendationRequest(selectedMovieIds=["tt0000001"])
    assert req.selected_movie_ids == ["tt0000001"]
    assert req.limit == 20
    assert req.page == 1
    assert req.page_size == 20

def test_recommendation_item():
    item = RecommendationItem(
        id="tt0000001",
        titleType="short",
        primaryTitle="Carmencita",
        originalTitle="Carmencita",
        isAdult=False,
        startYear=1894,
        endYear=None,
        runtimeMinutes=1,
        genres=["Documentary", "Short"],
        averageRating=5.7,
        numVotes=1900,
        recommendationScore=9.5,
        sharedGenres=2,
        sharedPeople=1,
        sharedCrew=0,
        sharedTitleTypes=1,
    )
    assert item.recommendation_score == 9.5
    assert item.shared_genres == 2
    assert item.shared_people == 1
    assert item.shared_crew == 0
    assert item.shared_title_types == 1

def test_recommendation_response():
    resp = RecommendationResponse(
        data=[],
        meta=PaginationMeta(page=1, pageSize=20, total=0, totalPages=0)
    )
    assert resp.data == []
    assert resp.meta.page == 1
