from __future__ import annotations

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

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


def database_schema_matches_metadata(connection: Connection) -> bool:
    migration_context = MigrationContext.configure(
        connection,
        opts={
            "compare_type": True,
            "compare_server_default": True,
        },
    )
    return not compare_metadata(migration_context, Base.metadata)


def upgrade_database(database_url: str | None = None) -> str:
    config = get_alembic_config(database_url)
    engine = get_engine(database_url, apply_sqlite_pragmas=False)
    action: str
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            has_version_table = inspector.has_table("alembic_version")
            existing_tables = inspector.get_table_names()

            if not has_version_table:
                if not existing_tables:
                    action = "upgrade"
                elif database_schema_matches_metadata(connection):
                    action = "stamp"
                else:
                    raise RuntimeError(
                        "Refusing to stamp an existing database without alembic_version because its schema does not "
                        "exactly match the current metadata. Run a deliberate legacy baseline step first."
                    )
            else:
                action = "upgrade"
    finally:
        engine.dispose()

    if action == "stamp":
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
