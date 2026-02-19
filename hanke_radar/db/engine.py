"""Database engine and session management."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hanke_radar.config import settings


def _convert_neon_url(url: str) -> str:
    """Convert a Neon PostgreSQL URL for asyncpg compatibility.

    asyncpg doesn't accept sslmode or channel_binding as query params.
    We strip them and pass ssl=True via connect_args instead.
    """
    if not url:
        return url

    # Swap driver prefix
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Parse and strip unsupported query params
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params.pop("sslmode", None)
    params.pop("channel_binding", None)
    clean_query = urlencode({k: v[0] for k, v in params.items()}) if params else ""
    return urlunparse(parsed._replace(query=clean_query))


_db_url = _convert_neon_url(settings.database_url)

# asyncpg needs ssl=True for Neon (replaces sslmode=require)
_connect_args = {"ssl": True} if _db_url else {}

engine = create_async_engine(
    _db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
) if _db_url else None

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
) if engine else None


async def get_session() -> AsyncSession:
    """Yield an async database session."""
    if async_session is None:
        raise RuntimeError("DATABASE_URL not configured")
    async with async_session() as session:
        yield session
