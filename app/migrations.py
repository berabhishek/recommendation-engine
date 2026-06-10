from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.database import DATABASE_URL, get_engine
from app.models import Base

ALEMBIC_INI_PATH = Path(__file__).resolve().parent.parent / "alembic.ini"


def get_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", database_url or DATABASE_URL)
    return config


def get_head_revision(database_url: str | None = None) -> str:
    config = get_alembic_config(database_url)
    return ScriptDirectory.from_config(config).get_current_head()


def database_has_current_schema(database_url: str | None = None) -> bool:
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        return set(Base.metadata.tables) <= existing_tables
    finally:
        engine.dispose()


def upgrade_database(database_url: str | None = None) -> str:
    config = get_alembic_config(database_url)
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    try:
        inspector = inspect(engine)
        has_version_table = inspector.has_table("alembic_version")
    finally:
        engine.dispose()

    if not has_version_table and database_has_current_schema(database_url):
        command.stamp(config, "head")
    else:
        command.upgrade(config, "head")
    return get_head_revision(database_url)


def get_current_database_revision(database_url: str | None = None) -> str | None:
    engine = get_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:
        return None
    finally:
        engine.dispose()
