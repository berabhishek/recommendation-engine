from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import DATABASE_URL as SETTINGS_DATABASE_URL

DATABASE_URL = SETTINGS_DATABASE_URL


class Base(DeclarativeBase):
    pass


def get_database_url(database_url: str | None = None) -> str:
    return database_url or DATABASE_URL


def get_engine(database_url: str | None = None, apply_sqlite_pragmas: bool = True) -> Engine:
    url = get_database_url(database_url)
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        ensure_parent_dir(url)

    engine = create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)

    if url.startswith("sqlite") and apply_sqlite_pragmas:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA temp_store = MEMORY")
            cursor.execute("PRAGMA cache_size = -200000")
            cursor.execute("PRAGMA mmap_size = 268435456")
            cursor.close()

    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ensure_parent_dir(database_url: str | None = None) -> None:
    url = get_database_url(database_url)
    if not url.startswith("sqlite"):
        return

    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return

    db_path = Path(url.removeprefix(prefix))
    db_path.parent.mkdir(parents=True, exist_ok=True)


def recreate_schema(engine: Engine, drop_existing: bool = True) -> None:
    import app.models  # noqa: F401

    if drop_existing:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def drop_indexes(engine: Engine) -> None:
    import app.models  # noqa: F401

    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.drop(bind=engine, checkfirst=True)


def create_indexes(engine: Engine) -> None:
    import app.models  # noqa: F401

    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)


def get_db(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
