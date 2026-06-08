import pytest
from sqlalchemy import create_engine, text
from app.database import (
    get_database_url,
    get_engine,
    get_session_factory,
    ensure_parent_dir,
    recreate_schema,
    drop_indexes,
    create_indexes,
    get_db,
)
from app.settings import DATABASE_URL
import tempfile
import os
from pathlib import Path

def test_get_database_url():
    assert get_database_url(None) == DATABASE_URL
    assert get_database_url("sqlite:///foo.db") == "sqlite:///foo.db"

def test_ensure_parent_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "nested" / "db.sqlite"
        url = f"sqlite:///{db_path}"
        ensure_parent_dir(url)
        assert db_path.parent.exists()

def test_ensure_parent_dir_non_sqlite():
    # Should be a no-op
    ensure_parent_dir("postgresql://user:pass@localhost/db")

def test_ensure_parent_dir_sqlite_invalid_prefix():
    # Should return on line 51
    ensure_parent_dir("sqlite://memory")

def test_get_engine_sqlite():
    engine = get_engine("sqlite:///:memory:")
    assert engine.name == "sqlite"
    # Execute a query to trigger connect event
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

def test_get_session_factory():
    engine = get_engine("sqlite:///:memory:")
    factory = get_session_factory(engine)
    session = factory()
    assert session.bind == engine
    session.close()

def test_recreate_schema():
    engine = get_engine("sqlite:///:memory:")
    recreate_schema(engine, drop_existing=True)

def test_drop_create_indexes():
    engine = get_engine("sqlite:///:memory:")
    recreate_schema(engine, drop_existing=False)
    drop_indexes(engine)
    create_indexes(engine)

def test_get_db():
    engine = get_engine("sqlite:///:memory:")
    factory = get_session_factory(engine)
    db_gen = get_db(factory)
    session = next(db_gen)
    assert session is not None
    with pytest.raises(StopIteration):
        next(db_gen)
