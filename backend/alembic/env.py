from logging.config import fileConfig

from alembic import context
from app.db.engine import create_async_engine_and_session
from app.db.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_online():
    # Create async engine via our helper so it uses Cloud SQL connector
    engine, _ = create_async_engine_and_session()

    connectable = engine

    with connectable.connect() as connection:  # type: ignore
        context.configure(connection=connection, target_metadata=Base.metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("offline mode not supported; run alembic with DB available")
else:
    run_migrations_online()
