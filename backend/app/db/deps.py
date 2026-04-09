from typing import AsyncGenerator

from app.db.engine import async_session


async def get_db() -> AsyncGenerator:
    """Yield an AsyncSession for dependency injection.

    NOTE: async_session is created in app.db.engine and may be None in test
    environments until configured. Configure CLOUD_SQL_INSTANCE, DB_USER,
    DB_PASSWORD and DB_NAME in your environment before running migrations.
    """
    if async_session is None:
        raise RuntimeError(
            "Database async_session not configured. Set CLOUD_SQL_INSTANCE and DB_* env vars."
        )

    async with async_session() as session:
        yield session
