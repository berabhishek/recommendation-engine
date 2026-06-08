from __future__ import annotations

from collections.abc import Generator, Sequence

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import Select, and_, exists, func, literal, or_, select
from sqlalchemy.orm import Session

from app.database import get_engine, get_session_factory, recreate_schema
from app.models import Movie, MovieAka, MovieCrewLink, MovieEpisode, MovieGenre, MoviePrincipal, MovieRating
from app.schemas import (
    MovieDetail,
    MovieListResponse,
    MovieSummary,
    PaginationMeta,
    RecommendationItem,
    RecommendationRequest,
    RecommendationResponse,
)
from app.settings import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


app = FastAPI(
    title="Recommendation Engine API",
    version="0.1.0",
    description="FastAPI + SQLAlchemy movie recommendation API backed by IMDb gzip imports.",
)

engine = get_engine()
session_factory = get_session_factory(engine)


@app.on_event("startup")
def _startup() -> None:
    recreate_schema(engine, drop_existing=False)


def db_session() -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


def get_page(page: int | None) -> int:
    return page if page and page > 0 else 1


def get_page_size(page_size: int | None) -> int:
    if not page_size or page_size <= 0:
        return DEFAULT_PAGE_SIZE
    return min(page_size, MAX_PAGE_SIZE)


def split_csv(values: str | None) -> list[str]:
    if not values:
        return []
    return [item.strip() for item in values.split(",") if item.strip()]


def movie_summary_row(row: dict[str, object]) -> MovieSummary:
    genres = row.get("genres") or []
    if isinstance(genres, str):
        genres = split_csv(genres)
    return MovieSummary(
        id=row["id"],
        titleType=row["title_type"],
        primaryTitle=row["primary_title"],
        originalTitle=row["original_title"],
        isAdult=bool(row["is_adult"]),
        startYear=row.get("start_year"),
        endYear=row.get("end_year"),
        runtimeMinutes=row.get("runtime_minutes"),
        genres=list(genres),
        averageRating=row.get("average_rating"),
        numVotes=row.get("num_votes"),
    )


def pagination_meta(page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(page=page, page_size=page_size, total=total, total_pages=max(1, (total + page_size - 1) // page_size))


def base_movie_query(
    q: str | None = None,
    title_type: str | None = None,
    genres: Sequence[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    min_rating: float | None = None,
    min_votes: int | None = None,
) -> Select[tuple[str]]:
    stmt = select(Movie.id).distinct()

    if min_rating is not None or min_votes is not None:
        stmt = stmt.join(MovieRating, MovieRating.movie_id == Movie.id)

    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append(or_(Movie.primary_title.ilike(like), Movie.original_title.ilike(like)))
    if title_type:
        conditions.append(Movie.title_type == title_type)
    if year_min is not None:
        conditions.append(Movie.start_year >= year_min)
    if year_max is not None:
        conditions.append(Movie.start_year <= year_max)
    if min_rating is not None:
        conditions.append(MovieRating.average_rating >= min_rating)
    if min_votes is not None:
        conditions.append(MovieRating.num_votes >= min_votes)
    if genres:
        conditions.append(
            exists(
                select(1)
                .select_from(MovieGenre)
                .where(MovieGenre.movie_id == Movie.id, MovieGenre.genre.in_(list(genres)))
            )
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt


def list_movies_query(
    page: int,
    page_size: int,
    sort_by: str,
    sort_dir: str,
    q: str | None,
    title_type: str | None,
    genres: Sequence[str] | None,
    year_min: int | None,
    year_max: int | None,
    min_rating: float | None,
    min_votes: int | None,
):
    filtered_ids = base_movie_query(q, title_type, genres, year_min, year_max, min_rating, min_votes).cte("filtered_ids")
    genre_agg = (
        select(MovieGenre.movie_id.label("movie_id"), func.group_concat(MovieGenre.genre, ",").label("genres"))
        .group_by(MovieGenre.movie_id)
        .cte("genre_agg")
    )
    rating = MovieRating
    stmt = (
        select(
            Movie.id.label("id"),
            Movie.title_type.label("title_type"),
            Movie.primary_title.label("primary_title"),
            Movie.original_title.label("original_title"),
            Movie.is_adult.label("is_adult"),
            Movie.start_year.label("start_year"),
            Movie.end_year.label("end_year"),
            Movie.runtime_minutes.label("runtime_minutes"),
            func.coalesce(genre_agg.c.genres, literal("")).label("genres"),
            rating.average_rating.label("average_rating"),
            rating.num_votes.label("num_votes"),
        )
        .select_from(Movie)
        .join(filtered_ids, filtered_ids.c.id == Movie.id)
        .outerjoin(genre_agg, genre_agg.c.movie_id == Movie.id)
        .outerjoin(rating, rating.movie_id == Movie.id)
    )

    sort_direction = sort_dir.lower()
    descending = sort_direction != "asc"
    sort_map = {
        "title": Movie.primary_title,
        "year": Movie.start_year,
        "rating": rating.average_rating,
        "votes": rating.num_votes,
        "runtime": Movie.runtime_minutes,
    }
    sort_column = sort_map.get(sort_by, rating.average_rating)
    if descending:
        stmt = stmt.order_by(sort_column.desc().nullslast(), Movie.primary_title.asc())
    else:
        stmt = stmt.order_by(sort_column.asc().nullsfirst(), Movie.primary_title.asc())

    stmt = stmt.limit(page_size).offset((page - 1) * page_size)
    count_stmt = select(func.count()).select_from(filtered_ids)
    return stmt, count_stmt


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/movies", response_model=MovieListResponse)
def list_movies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, alias="pageSize"),
    sort_by: str = Query(default="rating", alias="sortBy"),
    sort_dir: str = Query(default="desc", alias="sortDir"),
    q: str | None = None,
    title_type: str | None = Query(default=None, alias="titleType"),
    genres: str | None = None,
    year_min: int | None = Query(default=None, alias="yearMin"),
    year_max: int | None = Query(default=None, alias="yearMax"),
    min_rating: float | None = Query(default=None, alias="minRating"),
    min_votes: int | None = Query(default=None, alias="minVotes"),
    session: Session = Depends(db_session),
):
    genre_list = split_csv(genres)
    stmt, count_stmt = list_movies_query(page, page_size, sort_by, sort_dir, q, title_type, genre_list, year_min, year_max, min_rating, min_votes)
    rows = session.execute(stmt).mappings().all()
    total = session.scalar(count_stmt) or 0
    data = [movie_summary_row(row) for row in rows]
    return MovieListResponse(data=data, meta=pagination_meta(page, page_size, total))


@app.get("/movies/{movie_id}", response_model=MovieDetail)
def get_movie(movie_id: str, session: Session = Depends(db_session)):
    genre_agg = (
        select(MovieGenre.movie_id.label("movie_id"), func.group_concat(MovieGenre.genre, ",").label("genres"))
        .group_by(MovieGenre.movie_id)
        .cte("genre_agg_detail")
    )
    movie = session.execute(
        select(
            Movie.id.label("id"),
            Movie.title_type.label("title_type"),
            Movie.primary_title.label("primary_title"),
            Movie.original_title.label("original_title"),
            Movie.is_adult.label("is_adult"),
            Movie.start_year.label("start_year"),
            Movie.end_year.label("end_year"),
            Movie.runtime_minutes.label("runtime_minutes"),
            func.coalesce(genre_agg.c.genres, literal("")).label("genres"),
            MovieRating.average_rating.label("average_rating"),
            MovieRating.num_votes.label("num_votes"),
        )
        .select_from(Movie)
        .outerjoin(genre_agg, genre_agg.c.movie_id == Movie.id)
        .outerjoin(MovieRating, MovieRating.movie_id == Movie.id)
        .where(Movie.id == movie_id)
    ).mappings().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    akas = session.execute(
        select(MovieAka.ordering, MovieAka.title, MovieAka.region, MovieAka.language, MovieAka.types, MovieAka.attributes, MovieAka.is_original_title)
        .where(MovieAka.movie_id == movie_id)
        .order_by(MovieAka.ordering.asc())
    ).mappings().all()
    principals = session.execute(
        select(MoviePrincipal.ordering, MoviePrincipal.person_id, MoviePrincipal.category, MoviePrincipal.job, MoviePrincipal.characters)
        .where(MoviePrincipal.movie_id == movie_id)
        .order_by(MoviePrincipal.ordering.asc())
        .limit(50)
    ).mappings().all()
    crew_links = session.execute(
        select(MovieCrewLink.person_id, MovieCrewLink.role).where(MovieCrewLink.movie_id == movie_id).order_by(MovieCrewLink.role.asc())
    ).mappings().all()
    episode = session.execute(
        select(MovieEpisode.parent_movie_id, MovieEpisode.season_number, MovieEpisode.episode_number).where(MovieEpisode.movie_id == movie_id)
    ).mappings().first()

    return MovieDetail(
        **movie_summary_row(movie).model_dump(),
        akas=[dict(item) for item in akas],
        principals=[dict(item) for item in principals],
        crew_links=[dict(item) for item in crew_links],
        episode=dict(episode) if episode else None,
    )
@app.post("/recommendations", response_model=RecommendationResponse)
def recommend_movies(payload: RecommendationRequest, session: Session = Depends(db_session)):
    if not payload.selected_movie_ids:
        raise HTTPException(status_code=400, detail="selectedMovieIds cannot be empty")

    selected_ids = list(dict.fromkeys(payload.selected_movie_ids))
    selected_movies = session.execute(
        select(Movie.id, Movie.title_type).where(Movie.id.in_(selected_ids))
    ).mappings().all()
    if not selected_movies:
        raise HTTPException(status_code=404, detail="None of the selected movies were found")

    selected_genres = set(
        session.execute(
            select(MovieGenre.genre).where(MovieGenre.movie_id.in_([row["id"] for row in selected_movies]))
        ).scalars()
    )
    selected_people = set(
        session.execute(
            select(MoviePrincipal.person_id).where(MoviePrincipal.movie_id.in_([row["id"] for row in selected_movies]))
        ).scalars()
    )
    selected_people.update(
        session.execute(
            select(MovieCrewLink.person_id).where(MovieCrewLink.movie_id.in_([row["id"] for row in selected_movies]))
        ).scalars()
    )
    selected_types = {row["title_type"] for row in selected_movies}

    genre_agg = (
        select(MovieGenre.movie_id.label("movie_id"), func.group_concat(MovieGenre.genre, ",").label("genres"))
        .group_by(MovieGenre.movie_id)
        .cte("candidate_genre_agg")
    )
    candidate_filters = [Movie.id.notin_(selected_ids)]
    if selected_genres:
        candidate_filters.append(
            exists(
                select(1)
                .select_from(MovieGenre)
                .where(MovieGenre.movie_id == Movie.id, MovieGenre.genre.in_(list(selected_genres)))
            )
        )
    if selected_types:
        candidate_filters.append(Movie.title_type.in_(list(selected_types)))

    candidate_stmt = (
        select(
            Movie.id.label("id"),
            Movie.title_type.label("title_type"),
            Movie.primary_title.label("primary_title"),
            Movie.original_title.label("original_title"),
            Movie.is_adult.label("is_adult"),
            Movie.start_year.label("start_year"),
            Movie.end_year.label("end_year"),
            Movie.runtime_minutes.label("runtime_minutes"),
            func.coalesce(genre_agg.c.genres, literal("")).label("genres"),
            MovieRating.average_rating.label("average_rating"),
            MovieRating.num_votes.label("num_votes"),
        )
        .select_from(Movie)
        .outerjoin(MovieRating, MovieRating.movie_id == Movie.id)
        .outerjoin(genre_agg, genre_agg.c.movie_id == Movie.id)
        .where(and_(*candidate_filters))
        .order_by(MovieRating.average_rating.desc().nullslast(), MovieRating.num_votes.desc().nullslast(), Movie.primary_title.asc())
        .limit(2000)
    )
    candidate_rows = session.execute(candidate_stmt).mappings().all()
    candidate_ids = [row["id"] for row in candidate_rows]

    principal_people: dict[str, set[str]] = {}
    if candidate_ids:
        for movie_id, person_id in session.execute(
            select(MoviePrincipal.movie_id, MoviePrincipal.person_id).where(MoviePrincipal.movie_id.in_(candidate_ids))
        ):
            principal_people.setdefault(movie_id, set()).add(person_id)

    crew_people: dict[str, set[str]] = {}
    if candidate_ids:
        for movie_id, person_id in session.execute(
            select(MovieCrewLink.movie_id, MovieCrewLink.person_id).where(MovieCrewLink.movie_id.in_(candidate_ids))
        ):
            crew_people.setdefault(movie_id, set()).add(person_id)

    scored: list[RecommendationItem] = []
    for row in candidate_rows:
        movie_id = row["id"]
        genres = set(split_csv(row["genres"]))
        principal_set = principal_people.get(movie_id, set())
        crew_set = crew_people.get(movie_id, set())
        shared_genres = len(genres & selected_genres)
        shared_people = len(principal_set & selected_people)
        shared_crew = len(crew_set & selected_people)
        shared_title_types = 1 if row["title_type"] in selected_types else 0
        average_rating = row["average_rating"] or 0.0
        num_votes = row["num_votes"] or 0
        recommendation_score = (
            shared_genres * 4.0
            + shared_people * 2.0
            + shared_crew * 1.5
            + shared_title_types * 1.0
            + average_rating * 1.2
            + min(num_votes, 100000) / 100000.0
        )
        scored.append(
            RecommendationItem(
                id=movie_id,
                titleType=row["title_type"],
                primaryTitle=row["primary_title"],
                originalTitle=row["original_title"],
                isAdult=bool(row["is_adult"]),
                startYear=row["start_year"],
                endYear=row["end_year"],
                runtimeMinutes=row["runtime_minutes"],
                genres=list(genres),
                averageRating=average_rating,
                numVotes=num_votes,
                recommendationScore=recommendation_score,
                sharedGenres=shared_genres,
                sharedPeople=shared_people,
                sharedCrew=shared_crew,
                sharedTitleTypes=shared_title_types,
            )
        )

    scored.sort(
        key=lambda item: (
            item.recommendation_score,
            item.average_rating or 0.0,
            item.num_votes or 0,
            item.primary_title,
        ),
        reverse=True,
    )
    page = get_page(payload.page)
    page_size = get_page_size(payload.page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = scored[start:end]
    total = len(scored)
    return RecommendationResponse(data=page_items, meta=pagination_meta(page, page_size, total))


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=3000, reload=False)


if __name__ == "__main__":
    main()
