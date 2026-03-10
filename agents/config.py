"""
Scout AI - Agent Configuration

Central configuration for all agent services, API keys, model selection,
and runtime parameters. Values are loaded from environment variables with
sensible defaults for local development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AnthropicConfig:
    """Anthropic / Claude model configuration."""

    api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    synthesis_model: str = "claude-sonnet-4-20250514"
    classification_model: str = "claude-haiku-4-5-20251001"
    max_tokens_synthesis: int = 8192
    max_tokens_classification: int = 2048
    temperature_synthesis: float = 0.3
    temperature_classification: float = 0.1


@dataclass(frozen=True)
class FirecrawlConfig:
    """Firecrawl web-scraping service configuration."""

    api_key: str = field(
        default_factory=lambda: os.environ.get("FIRECRAWL_API_KEY", "")
    )
    base_url: str = field(
        default_factory=lambda: os.environ.get(
            "FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v1"
        )
    )
    timeout: int = 30


@dataclass(frozen=True)
class ResendConfig:
    """Resend email delivery configuration."""

    api_key: str = field(
        default_factory=lambda: os.environ.get("RESEND_API_KEY", "")
    )
    from_address: str = field(
        default_factory=lambda: os.environ.get(
            "RESEND_FROM_ADDRESS", "briefings@scoutai.app"
        )
    )


@dataclass(frozen=True)
class SlackConfig:
    """Slack Bolt delivery configuration."""

    bot_token: str = field(
        default_factory=lambda: os.environ.get("SLACK_BOT_TOKEN", "")
    )
    signing_secret: str = field(
        default_factory=lambda: os.environ.get("SLACK_SIGNING_SECRET", "")
    )
    default_channel: str = field(
        default_factory=lambda: os.environ.get(
            "SLACK_DEFAULT_CHANNEL", "#competitive-intel"
        )
    )


@dataclass(frozen=True)
class WebhookConfig:
    """Generic webhook delivery configuration."""

    url: Optional[str] = field(
        default_factory=lambda: os.environ.get("WEBHOOK_URL")
    )
    secret: Optional[str] = field(
        default_factory=lambda: os.environ.get("WEBHOOK_SECRET")
    )


@dataclass(frozen=True)
class WebSearchConfig:
    """Web search (SerpAPI / Serper) configuration."""

    provider: str = field(
        default_factory=lambda: os.environ.get("SEARCH_PROVIDER", "serper")
    )
    api_key: str = field(
        default_factory=lambda: os.environ.get("SEARCH_API_KEY", "")
    )
    serper_base_url: str = "https://google.serper.dev"
    max_results: int = 10


@dataclass(frozen=True)
class DatabaseConfig:
    """Persistence layer configuration (Supabase / Postgres)."""

    supabase_url: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_URL", "")
    )
    supabase_key: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_SERVICE_KEY", "")
    )


@dataclass(frozen=True)
class PipelineConfig:
    """Top-level pipeline tuning knobs."""

    # How many competitors to process concurrently
    max_concurrent_competitors: int = 5
    # Significance threshold: changes below this are dropped before synthesis
    min_change_significance: float = 0.3
    # Maximum age (hours) for cached snapshots before re-scraping
    snapshot_ttl_hours: int = 24
    # Retry budget per agent
    agent_max_retries: int = 3
    agent_retry_delay_seconds: float = 2.0


@dataclass(frozen=True)
class Settings:
    """Aggregate settings object - single source of truth."""

    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    firecrawl: FirecrawlConfig = field(default_factory=FirecrawlConfig)
    resend: ResendConfig = field(default_factory=ResendConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    web_search: WebSearchConfig = field(default_factory=WebSearchConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )


# Module-level singleton used across agents
settings = Settings()
