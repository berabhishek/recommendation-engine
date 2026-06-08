import pytest
from app.models import (
    Movie,
    MovieGenre,
    MovieRating,
    Person,
    PersonProfession,
    PersonKnownForTitle,
    MoviePrincipal,
    MovieAka,
    MovieCrewLink,
    MovieEpisode,
)

def test_models_instantiation():
    # Just creating instances to make sure they're mapped correctly
    movie = Movie(
        id="tt123",
        title_type="movie",
        primary_title="Test",
        original_title="Test",
        is_adult=False,
        start_year=2020,
    )
    assert movie.id == "tt123"

    genre = MovieGenre(movie_id="tt123", genre="Action")
    assert genre.genre == "Action"

    rating = MovieRating(movie_id="tt123", average_rating=5.0, num_votes=100)
    assert rating.average_rating == 5.0

    person = Person(id="nm123", primary_name="John Doe")
    assert person.primary_name == "John Doe"

    prof = PersonProfession(person_id="nm123", profession="actor")
    assert prof.profession == "actor"

    known_for = PersonKnownForTitle(person_id="nm123", movie_id="tt123", position=1)
    assert known_for.position == 1

    principal = MoviePrincipal(
        movie_id="tt123", ordering=1, person_id="nm123", category="actor"
    )
    assert principal.ordering == 1

    aka = MovieAka(
        movie_id="tt123", ordering=1, title="Test AKA", is_original_title=False
    )
    assert aka.title == "Test AKA"

    crew_link = MovieCrewLink(movie_id="tt123", person_id="nm123", role="director")
    assert crew_link.role == "director"

    episode = MovieEpisode(
        movie_id="tt124", parent_movie_id="tt123", season_number=1, episode_number=1
    )
    assert episode.season_number == 1
