FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the `uv` launcher (contains a prebuilt binary at /uv)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (will use the lockfile and create an isolated env)
RUN uv sync --frozen --no-dev

# Copy app sources
COPY . .

EXPOSE 8080

# Start via uv so the binary environment it created is used and uvicorn is in PATH
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
