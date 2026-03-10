"""Structured logging configuration for Scout AI.

Provides a consistent logging setup across the application:
- JSON-formatted logs in production
- Human-readable logs in development
- Contextual fields for agent runs, pipeline execution, and LLM calls
- Optional Sentry breadcrumb integration
"""

import logging
import time
from contextvars import ContextVar
from typing import Any

# Context variables for request/pipeline-scoped logging
_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)
_agent_name: ContextVar[str | None] = ContextVar("agent_name", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_log_context(
    *,
    run_id: str | None = None,
    agent_name: str | None = None,
    user_id: str | None = None,
) -> None:
    """Set contextual fields for structured log entries."""
    if run_id is not None:
        _run_id.set(run_id)
    if agent_name is not None:
        _agent_name.set(agent_name)
    if user_id is not None:
        _user_id.set(user_id)


def clear_log_context() -> None:
    """Reset all contextual log fields."""
    _run_id.set(None)
    _agent_name.set(None)
    _user_id.set(None)


class ContextFilter(logging.Filter):
    """Inject context variables into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = _run_id.get()  # type: ignore[attr-defined]
        record.agent_name = _agent_name.get()  # type: ignore[attr-defined]
        record.user_id = _user_id.get()  # type: ignore[attr-defined]
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a logger pre-configured with the Scout AI context filter.

    Usage:
        from apps.api.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Processing competitor", extra={"competitor": "Acme"})
    """
    logger = logging.getLogger(name)
    if not any(isinstance(f, ContextFilter) for f in logger.filters):
        logger.addFilter(ContextFilter())
    return logger


def log_agent_run(
    logger: logging.Logger,
    agent_name: str,
    *,
    run_id: str | None = None,
    status: str = "started",
    duration_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured log entry for an agent run lifecycle event.

    Args:
        logger: The logger instance to use.
        agent_name: Name of the agent (e.g. "web_monitor", "synthesis").
        run_id: Pipeline run ID.
        status: One of "started", "completed", "failed".
        duration_ms: Elapsed time in milliseconds (for completed/failed).
        extra: Additional key-value pairs to include.
    """
    msg_parts = [f"agent={agent_name}", f"status={status}"]
    if run_id:
        msg_parts.append(f"run_id={run_id}")
    if duration_ms is not None:
        msg_parts.append(f"duration_ms={duration_ms:.1f}")
    if extra:
        for k, v in extra.items():
            msg_parts.append(f"{k}={v}")

    message = " | ".join(msg_parts)

    if status == "failed":
        logger.error(message)
    else:
        logger.info(message)


def log_llm_call(
    logger: logging.Logger,
    *,
    model: str,
    purpose: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    duration_ms: float | None = None,
    success: bool = True,
    error: str | None = None,
) -> None:
    """Log an LLM API call with token usage and timing."""
    parts = [f"llm_call purpose={purpose}", f"model={model}"]
    if input_tokens is not None:
        parts.append(f"input_tokens={input_tokens}")
    if output_tokens is not None:
        parts.append(f"output_tokens={output_tokens}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.1f}")
    parts.append(f"success={success}")
    if error:
        parts.append(f"error={error}")

    message = " | ".join(parts)
    if success:
        logger.info(message)
    else:
        logger.warning(message)


class TimedOperation:
    """Context manager for timing operations and logging the result.

    Usage:
        with TimedOperation(logger, "crawl_website", url=url):
            result = await scrape(url)
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        **extra: Any,
    ) -> None:
        self.logger = logger
        self.operation = operation
        self.extra = extra
        self._start: float = 0

    def __enter__(self) -> "TimedOperation":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        parts = [f"op={self.operation}", f"duration_ms={elapsed_ms:.1f}"]
        for k, v in self.extra.items():
            parts.append(f"{k}={v}")

        if exc_type is not None:
            parts.append(f"error={exc_val}")
            self.logger.error(" | ".join(parts))
        else:
            self.logger.info(" | ".join(parts))
