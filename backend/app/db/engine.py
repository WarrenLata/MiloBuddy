import os
from typing import Optional

from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# IMPORTANT: configure these environment variables in your .env or Cloud Run
# - CLOUD_SQL_INSTANCE : GCP instance connection name: PROJECT:europe-west9:INSTANCE
# - DB_USER
# - DB_PASSWORD
# - DB_NAME
# The connector will use PRIVATE IP by default.


_connector: Optional[Connector] = None


def _get_connector() -> Connector:
    global _connector
    if _connector is None:
        _connector = Connector()
    return _connector


def create_async_engine_and_session():
    instance_conn_name = os.environ.get("CLOUD_SQL_INSTANCE")
    if not instance_conn_name:
        raise RuntimeError(
            "CLOUD_SQL_INSTANCE not set (format: PROJECT:europe-west9:INSTANCE)"
        )

    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    db_name = os.environ.get("DB_NAME") or settings.project_name.lower()

    connector = _get_connector()

    async def getconn():
        # Use the Cloud SQL Python Connector in async mode with asyncpg
        # NOTE: this requires the cloud-sql-python-connector [async] and asyncpg.
        conn = await connector.connect(
            instance_conn_name,
            "asyncpg",
            user=user,
            password=password,
            db=db_name,
            ip_type=IPTypes.PRIVATE,
        )
        return conn

    # SQLAlchemy async engine with an empty URL; the connector provides connections
    engine = create_async_engine(
        "postgresql+asyncpg://",
        creator=lambda: getconn(),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )

    async_session = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    return engine, async_session


# Create module-level engine/session for import convenience. This will raise
# at import time if required env vars are not present — keep that in mind for
# local dev and tests.
try:
    engine, async_session = create_async_engine_and_session()
except Exception:
    engine = None
    async_session = None
