"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Scout AI"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/scoutai"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Clerk Auth
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_jwks_url: str = "https://api.clerk.dev/v1/jwks"
    clerk_webhook_secret: str = ""
    clerk_issuer: str = ""
    clerk_enforce_mfa: bool = False  # Enforce MFA for all authenticated endpoints

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_growth: str = ""
    stripe_price_enterprise: str = ""

    # Resend (Email)
    resend_api_key: str = ""
    email_from: str = "Scout AI <notifications@scoutai.dev>"

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""

    # AI / LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Firecrawl
    firecrawl_api_key: str = ""

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # AWS (S3 for file storage)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "scoutai-assets"

    # Monitoring schedule (cron)
    monitoring_interval_hours: int = 6
    briefing_generation_day: str = "monday"
    briefing_generation_hour: int = 7

    # Flower (Celery monitoring)
    flower_port: int = 5555
    flower_basic_auth: str = ""  # username:password for Flower dashboard


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
