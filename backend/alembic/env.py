import asyncio
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


async def _run_migrations_async():
    """Run migrations using an async engine created by the project's helper.

    This uses SQLAlchemy AsyncEngine.connect() and connection.run_sync to
    execute the synchronous Alembic migration operations on the connection.
    """
    engine, _ = create_async_engine_and_session()
    if engine is None:
        raise RuntimeError(
            "No async engine available; check DATABASE_URL or CLOUD_SQL_INSTANCE"
        )

    async with engine.connect() as conn:  # type: ignore
        # run_sync will run the provided callable in a sync context
        await conn.run_sync(_do_run_migrations)


def _do_run_migrations(connection):
    """Synchronous function run inside a connection by run_sync.

    This configures the alembic context and runs migrations synchronously
    using the connection provided by the async engine's run_sync wrapper.
    """
    context.configure(connection=connection, target_metadata=Base.metadata)

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("offline mode not supported; run alembic with DB available")
else:
    asyncio.run(_run_migrations_async())
