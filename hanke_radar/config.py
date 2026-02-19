"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = ""

    # Scraper
    riigihanked_base_url: str = "https://riigihanked.riik.ee/rhr/api/public/v1"
    scrape_delay_seconds: float = 1.0  # polite rate limiting
    request_timeout_seconds: int = 120  # bulk XML can be large

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:3003",       # QuoteKit local
        "https://quote-kit.vercel.app",  # QuoteKit production
    ]

    model_config = {"env_file": ".env.local", "env_file_encoding": "utf-8"}


settings = Settings()
