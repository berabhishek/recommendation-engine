from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}


class MovieSummary(BaseModel):
    id: str
    title_type: str = Field(alias="titleType")
    primary_title: str = Field(alias="primaryTitle")
    original_title: str = Field(alias="originalTitle")
    is_adult: bool = Field(alias="isAdult")
    start_year: int | None = Field(alias="startYear")
    end_year: int | None = Field(alias="endYear")
    runtime_minutes: int | None = Field(alias="runtimeMinutes")
    genres: list[str] = Field(default_factory=list)
    average_rating: float | None = Field(default=None, alias="averageRating")
    num_votes: int | None = Field(default=None, alias="numVotes")

    model_config = {"populate_by_name": True}


class MovieDetail(MovieSummary):
    akas: list[dict[str, object]] = Field(default_factory=list)
    principals: list[dict[str, object]] = Field(default_factory=list)
    crew_links: list[dict[str, object]] = Field(default_factory=list, alias="crewLinks")
    episode: dict[str, object] | None = None

    model_config = {"populate_by_name": True}


class MovieListResponse(BaseModel):
    data: list[MovieSummary]
    meta: PaginationMeta


class RecommendationRequest(BaseModel):
    selected_movie_ids: list[str] = Field(min_length=1, alias="selectedMovieIds")
    limit: int = 20
    page: int = 1
    page_size: int = Field(default=20, alias="pageSize")

    model_config = {"populate_by_name": True}


class RecommendationItem(MovieSummary):
    recommendation_score: float = Field(alias="recommendationScore")
    shared_genres: int = Field(alias="sharedGenres")
    shared_people: int = Field(alias="sharedPeople")
    shared_crew: int = Field(alias="sharedCrew")
    shared_title_types: int = Field(alias="sharedTitleTypes")

    model_config = {"populate_by_name": True}


class RecommendationResponse(BaseModel):
    data: list[RecommendationItem]
    meta: PaginationMeta
