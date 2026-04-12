# MiloBuddy backend

## Local dev (Docker)

Start Postgres:

```powershell
docker compose up -d db
```

Run migrations (brings DB to the latest Alembic revision):

```powershell
docker compose run --rm api uv run alembic upgrade head
```

Create a new migration:

```powershell
# IMPORTANT: the DB must already be at head, otherwise you'll get:
# "Target database is not up to date."
docker compose run --rm api uv run alembic revision --autogenerate -m "your message"
```

If you *already* created the schema by other means and only need to align the
`alembic_version` table, stamp the current revision (be sure the schema matches):

```powershell
docker compose run --rm api uv run alembic stamp head
```

Reset the local DB (destructive: deletes the volume):

```powershell
docker compose down -v
docker compose up -d db
docker compose run --rm api uv run alembic upgrade head
```

## Running Alembic from your host shell (no Docker)

Alembic uses `DATABASE_URL` when running on your machine (see `app/db/engine.py`).

Example:

```powershell
$env:DATABASE_URL="postgresql+asyncpg://milo_app:localpassword@localhost:5432/milo_v1"
alembic upgrade head
```
