from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection

from app.database import Database
from app.models import Base
from app.settings import Settings

config = context.config
settings = Settings()
# Alembic represents the default PostgreSQL schema as None during autogeneration.
version_schema = (
    None
    if settings.alembic_version_schema == "public"
    else settings.alembic_version_schema
)
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        version_table_schema=version_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        if not isinstance(connection, Connection):
            raise TypeError("MIGRATION_CONNECTION_INVALID")
        run_migrations(connection)
        return

    database = Database(settings)
    try:
        with database.engine.connect() as connection:
            run_migrations(connection)
    finally:
        database.close()


if context.is_offline_mode():
    context.configure(
        url=settings.database_url,
        target_metadata=Base.metadata,
        version_table_schema=version_schema,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    run_online()
