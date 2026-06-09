from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    primary_title: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    original_title: Mapped[str] = mapped_column(String(512), nullable=False)
    genres_text: Mapped[str | None] = mapped_column(String(256))
    is_adult: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    start_year: Mapped[int | None] = mapped_column(Integer, index=True)
    end_year: Mapped[int | None] = mapped_column(Integer)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, index=True)

    rating = relationship("MovieRating", back_populates="movie", uselist=False, cascade="all, delete-orphan")
    genres = relationship("MovieGenre", back_populates="movie", cascade="all, delete-orphan")
    akas = relationship("MovieAka", back_populates="movie", cascade="all, delete-orphan")
    principals = relationship("MoviePrincipal", back_populates="movie", cascade="all, delete-orphan")
    crew_links = relationship("MovieCrewLink", back_populates="movie", cascade="all, delete-orphan")
    episodes = relationship(
        "MovieEpisode",
        back_populates="movie",
        cascade="all, delete-orphan",
        foreign_keys="MovieEpisode.movie_id",
    )


class MovieGenre(Base):
    __tablename__ = "movie_genres"
    __table_args__ = (UniqueConstraint("movie_id", "genre", name="uq_movie_genres_movie_genre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    genre: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    movie = relationship("Movie", back_populates="genres")


class MovieRating(Base):
    __tablename__ = "movie_ratings"

    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    average_rating: Mapped[float] = mapped_column(Float, nullable=False)
    num_votes: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    movie = relationship("Movie", back_populates="rating")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    primary_name: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    birth_year: Mapped[int | None] = mapped_column(Integer, index=True)
    death_year: Mapped[int | None] = mapped_column(Integer)

    professions = relationship("PersonProfession", back_populates="person", cascade="all, delete-orphan")
    known_for_titles = relationship("PersonKnownForTitle", back_populates="person", cascade="all, delete-orphan")
    principals = relationship("MoviePrincipal", back_populates="person", cascade="all, delete-orphan")
    crew_links = relationship("MovieCrewLink", back_populates="person", cascade="all, delete-orphan")


class PersonProfession(Base):
    __tablename__ = "person_professions"
    __table_args__ = (UniqueConstraint("person_id", "profession", name="uq_person_professions_person_profession"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True, nullable=False)
    profession: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    person = relationship("Person", back_populates="professions")


class PersonKnownForTitle(Base):
    __tablename__ = "person_known_for_titles"
    __table_args__ = (UniqueConstraint("person_id", "movie_id", name="uq_person_known_for_movie"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True, nullable=False)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    person = relationship("Person", back_populates="known_for_titles")


class MoviePrincipal(Base):
    __tablename__ = "movie_principals"
    __table_args__ = (UniqueConstraint("movie_id", "ordering", "person_id", name="uq_movie_principals_ordering"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    ordering: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    job: Mapped[str | None] = mapped_column(Text)
    characters: Mapped[str | None] = mapped_column(Text)

    movie = relationship("Movie", back_populates="principals")
    person = relationship("Person", back_populates="principals")


class MovieAka(Base):
    __tablename__ = "movie_akas"
    __table_args__ = (UniqueConstraint("movie_id", "ordering", "title", name="uq_movie_akas_ordering"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    ordering: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    region: Mapped[str | None] = mapped_column(String(32), index=True)
    language: Mapped[str | None] = mapped_column(String(32), index=True)
    types: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[str | None] = mapped_column(Text)
    is_original_title: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    movie = relationship("Movie", back_populates="akas")


class MovieCrewLink(Base):
    __tablename__ = "movie_crew_links"
    __table_args__ = (UniqueConstraint("movie_id", "person_id", "role", name="uq_movie_crew_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), index=True, nullable=False)

    movie = relationship("Movie", back_populates="crew_links")
    person = relationship("Person", back_populates="crew_links")


class MovieEpisode(Base):
    __tablename__ = "movie_episodes"

    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    parent_movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    season_number: Mapped[int | None] = mapped_column(Integer, index=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, index=True)

    movie = relationship("Movie", foreign_keys=[movie_id], back_populates="episodes")


class AppState(Base):
    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


Index("idx_movies_type_year", Movie.title_type, Movie.start_year)
Index("idx_movies_title_year", Movie.primary_title, Movie.start_year)
Index("idx_movie_genres_genre_movie", MovieGenre.genre, MovieGenre.movie_id)
Index("idx_ratings_votes_rating", MovieRating.num_votes, MovieRating.average_rating)
Index(
    "idx_ratings_rating_votes_movie",
    MovieRating.average_rating.desc(),
    MovieRating.num_votes.desc(),
    MovieRating.movie_id,
)
Index("idx_principals_movie_person", MoviePrincipal.movie_id, MoviePrincipal.person_id)
Index("idx_akas_movie_region", MovieAka.movie_id, MovieAka.region)
Index("idx_crew_movie_role", MovieCrewLink.movie_id, MovieCrewLink.role)
