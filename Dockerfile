FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY hanke_radar/ hanke_radar/

# Install the project itself
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Render injects PORT env var; default to 8000
CMD uv run uvicorn hanke_radar.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
