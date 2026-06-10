"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-06-10 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movies",
        sa.Column("id", sa.String(length=20), primary_key=True, nullable=False),
        sa.Column("title_type", sa.String(length=50), nullable=False),
        sa.Column("primary_title", sa.String(length=512), nullable=False),
        sa.Column("original_title", sa.String(length=512), nullable=False),
        sa.Column("genres_text", sa.String(length=256)),
        sa.Column("is_adult", sa.Boolean(), nullable=False),
        sa.Column("start_year", sa.Integer()),
        sa.Column("end_year", sa.Integer()),
        sa.Column("runtime_minutes", sa.Integer()),
    )
    op.create_table(
        "people",
        sa.Column("id", sa.String(length=20), primary_key=True, nullable=False),
        sa.Column("primary_name", sa.String(length=256), nullable=False),
        sa.Column("birth_year", sa.Integer()),
        sa.Column("death_year", sa.Integer()),
    )
    op.create_table(
        "app_state",
        sa.Column("key", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
    )
    op.create_table(
        "import_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("dataset_name", sa.String(length=128), nullable=False),
        sa.Column("dataset_version", sa.String(length=128)),
        sa.Column("importer_version", sa.String(length=64), nullable=False),
        sa.Column("alembic_revision", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("row_count", sa.Integer()),
        sa.Column("error_message", sa.Text()),
    )
    op.create_table(
        "movie_ratings",
        sa.Column("movie_id", sa.String(length=20), nullable=False),
        sa.Column("average_rating", sa.Float(), nullable=False),
        sa.Column("num_votes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("movie_id"),
    )
    op.create_table(
        "movie_genres",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.String(length=20), nullable=False),
        sa.Column("genre", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("movie_id", "genre", name="uq_movie_genres_movie_genre"),
    )
    op.create_table(
        "person_professions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("person_id", sa.String(length=20), nullable=False),
        sa.Column("profession", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("person_id", "profession", name="uq_person_professions_person_profession"),
    )
    op.create_table(
        "person_known_for_titles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("person_id", sa.String(length=20), nullable=False),
        sa.Column("movie_id", sa.String(length=20), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("person_id", "movie_id", name="uq_person_known_for_movie"),
    )
    op.create_table(
        "movie_principals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.String(length=20), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=64)),
        sa.Column("job", sa.Text()),
        sa.Column("characters", sa.Text()),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("movie_id", "ordering", "person_id", name="uq_movie_principals_ordering"),
    )
    op.create_table(
        "movie_akas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.String(length=20), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("region", sa.String(length=32)),
        sa.Column("language", sa.String(length=32)),
        sa.Column("types", sa.Text()),
        sa.Column("attributes", sa.Text()),
        sa.Column("is_original_title", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("movie_id", "ordering", "title", name="uq_movie_akas_ordering"),
    )
    op.create_table(
        "movie_crew_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.String(length=20), nullable=False),
        sa.Column("person_id", sa.String(length=20), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("movie_id", "person_id", "role", name="uq_movie_crew_role"),
    )
    op.create_table(
        "movie_episodes",
        sa.Column("movie_id", sa.String(length=20), primary_key=True, nullable=False),
        sa.Column("parent_movie_id", sa.String(length=20), nullable=False),
        sa.Column("season_number", sa.Integer()),
        sa.Column("episode_number", sa.Integer()),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_movie_id"], ["movies.id"], ondelete="CASCADE"),
    )

    op.create_index(op.f("ix_movies_title_type"), "movies", ["title_type"], unique=False)
    op.create_index(op.f("ix_movies_primary_title"), "movies", ["primary_title"], unique=False)
    op.create_index(op.f("ix_movies_start_year"), "movies", ["start_year"], unique=False)
    op.create_index(op.f("ix_movies_runtime_minutes"), "movies", ["runtime_minutes"], unique=False)
    op.create_index("idx_movies_type_year", "movies", ["title_type", "start_year"], unique=False)
    op.create_index("idx_movies_title_year", "movies", ["primary_title", "start_year"], unique=False)

    op.create_index(op.f("ix_people_primary_name"), "people", ["primary_name"], unique=False)
    op.create_index(op.f("ix_people_birth_year"), "people", ["birth_year"], unique=False)

    op.create_index(op.f("ix_movie_genres_movie_id"), "movie_genres", ["movie_id"], unique=False)
    op.create_index(op.f("ix_movie_genres_genre"), "movie_genres", ["genre"], unique=False)
    op.create_index(op.f("idx_movie_genres_genre_movie"), "movie_genres", ["genre", "movie_id"], unique=False)

    op.create_index(op.f("ix_movie_ratings_num_votes"), "movie_ratings", ["num_votes"], unique=False)
    op.create_index(
        "idx_ratings_votes_rating",
        "movie_ratings",
        ["num_votes", "average_rating"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX idx_ratings_rating_votes_movie "
        "ON movie_ratings (average_rating DESC, num_votes DESC, movie_id)"
    )

    op.create_index(op.f("ix_person_professions_person_id"), "person_professions", ["person_id"], unique=False)
    op.create_index(op.f("ix_person_professions_profession"), "person_professions", ["profession"], unique=False)

    op.create_index(op.f("ix_person_known_for_titles_person_id"), "person_known_for_titles", ["person_id"], unique=False)
    op.create_index(op.f("ix_person_known_for_titles_movie_id"), "person_known_for_titles", ["movie_id"], unique=False)

    op.create_index(op.f("ix_movie_principals_movie_id"), "movie_principals", ["movie_id"], unique=False)
    op.create_index(op.f("ix_movie_principals_ordering"), "movie_principals", ["ordering"], unique=False)
    op.create_index(op.f("ix_movie_principals_person_id"), "movie_principals", ["person_id"], unique=False)
    op.create_index(op.f("ix_movie_principals_category"), "movie_principals", ["category"], unique=False)
    op.create_index("idx_principals_movie_person", "movie_principals", ["movie_id", "person_id"], unique=False)

    op.create_index(op.f("ix_movie_akas_movie_id"), "movie_akas", ["movie_id"], unique=False)
    op.create_index(op.f("ix_movie_akas_ordering"), "movie_akas", ["ordering"], unique=False)
    op.create_index(op.f("ix_movie_akas_title"), "movie_akas", ["title"], unique=False)
    op.create_index(op.f("ix_movie_akas_region"), "movie_akas", ["region"], unique=False)
    op.create_index(op.f("ix_movie_akas_language"), "movie_akas", ["language"], unique=False)
    op.create_index("idx_akas_movie_region", "movie_akas", ["movie_id", "region"], unique=False)

    op.create_index(op.f("ix_movie_crew_links_movie_id"), "movie_crew_links", ["movie_id"], unique=False)
    op.create_index(op.f("ix_movie_crew_links_person_id"), "movie_crew_links", ["person_id"], unique=False)
    op.create_index(op.f("ix_movie_crew_links_role"), "movie_crew_links", ["role"], unique=False)
    op.create_index("idx_crew_movie_role", "movie_crew_links", ["movie_id", "role"], unique=False)

    op.create_index(op.f("ix_movie_episodes_parent_movie_id"), "movie_episodes", ["parent_movie_id"], unique=False)
    op.create_index(op.f("ix_movie_episodes_season_number"), "movie_episodes", ["season_number"], unique=False)
    op.create_index(op.f("ix_movie_episodes_episode_number"), "movie_episodes", ["episode_number"], unique=False)

    op.create_index(op.f("ix_import_runs_dataset_name"), "import_runs", ["dataset_name"], unique=False)
    op.create_index(op.f("ix_import_runs_alembic_revision"), "import_runs", ["alembic_revision"], unique=False)
    op.create_index(op.f("ix_import_runs_status"), "import_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_import_runs_status"), table_name="import_runs")
    op.drop_index(op.f("ix_import_runs_alembic_revision"), table_name="import_runs")
    op.drop_index(op.f("ix_import_runs_dataset_name"), table_name="import_runs")

    op.drop_index(op.f("ix_movie_episodes_episode_number"), table_name="movie_episodes")
    op.drop_index(op.f("ix_movie_episodes_season_number"), table_name="movie_episodes")
    op.drop_index(op.f("ix_movie_episodes_parent_movie_id"), table_name="movie_episodes")

    op.drop_index("idx_crew_movie_role", table_name="movie_crew_links")
    op.drop_index(op.f("ix_movie_crew_links_role"), table_name="movie_crew_links")
    op.drop_index(op.f("ix_movie_crew_links_person_id"), table_name="movie_crew_links")
    op.drop_index(op.f("ix_movie_crew_links_movie_id"), table_name="movie_crew_links")

    op.drop_index("idx_akas_movie_region", table_name="movie_akas")
    op.drop_index(op.f("ix_movie_akas_language"), table_name="movie_akas")
    op.drop_index(op.f("ix_movie_akas_region"), table_name="movie_akas")
    op.drop_index(op.f("ix_movie_akas_title"), table_name="movie_akas")
    op.drop_index(op.f("ix_movie_akas_ordering"), table_name="movie_akas")
    op.drop_index(op.f("ix_movie_akas_movie_id"), table_name="movie_akas")

    op.drop_index("idx_principals_movie_person", table_name="movie_principals")
    op.drop_index(op.f("ix_movie_principals_category"), table_name="movie_principals")
    op.drop_index(op.f("ix_movie_principals_person_id"), table_name="movie_principals")
    op.drop_index(op.f("ix_movie_principals_ordering"), table_name="movie_principals")
    op.drop_index(op.f("ix_movie_principals_movie_id"), table_name="movie_principals")

    op.drop_index(op.f("ix_person_known_for_titles_movie_id"), table_name="person_known_for_titles")
    op.drop_index(op.f("ix_person_known_for_titles_person_id"), table_name="person_known_for_titles")

    op.drop_index(op.f("ix_person_professions_profession"), table_name="person_professions")
    op.drop_index(op.f("ix_person_professions_person_id"), table_name="person_professions")

    op.drop_index("idx_ratings_rating_votes_movie", table_name="movie_ratings")
    op.drop_index("idx_ratings_votes_rating", table_name="movie_ratings")
    op.drop_index(op.f("ix_movie_ratings_num_votes"), table_name="movie_ratings")

    op.drop_index("idx_movie_genres_genre_movie", table_name="movie_genres")
    op.drop_index(op.f("ix_movie_genres_genre"), table_name="movie_genres")
    op.drop_index(op.f("ix_movie_genres_movie_id"), table_name="movie_genres")

    op.drop_index(op.f("ix_people_birth_year"), table_name="people")
    op.drop_index(op.f("ix_people_primary_name"), table_name="people")

    op.drop_index(op.f("ix_movies_runtime_minutes"), table_name="movies")
    op.drop_index(op.f("ix_movies_start_year"), table_name="movies")
    op.drop_index(op.f("ix_movies_primary_title"), table_name="movies")
    op.drop_index(op.f("ix_movies_title_type"), table_name="movies")
    op.drop_index("idx_movies_title_year", table_name="movies")
    op.drop_index("idx_movies_type_year", table_name="movies")

    op.drop_table("movie_episodes")
    op.drop_table("movie_crew_links")
    op.drop_table("movie_akas")
    op.drop_table("movie_principals")
    op.drop_table("person_known_for_titles")
    op.drop_table("person_professions")
    op.drop_table("movie_genres")
    op.drop_table("movie_ratings")
    op.drop_table("import_runs")
    op.drop_table("app_state")
    op.drop_table("people")
    op.drop_table("movies")
