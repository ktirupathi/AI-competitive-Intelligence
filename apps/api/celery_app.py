"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from .config import get_settings

settings = get_settings()

celery = Celery(
    "scoutai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_routes={
        "apps.api.tasks.monitoring.*": {"queue": "monitoring"},
        "apps.api.tasks.briefing_generation.*": {"queue": "briefings"},
    },
    beat_schedule={
        "monitor-competitors": {
            "task": "apps.api.tasks.monitoring.run_monitoring_cycle",
            "schedule": crontab(
                minute=0,
                hour=f"*/{settings.monitoring_interval_hours}",
            ),
        },
        "generate-weekly-briefings": {
            "task": "apps.api.tasks.briefing_generation.generate_all_briefings",
            "schedule": crontab(
                minute=0,
                hour=settings.briefing_generation_hour,
                day_of_week=settings.briefing_generation_day,
            ),
        },
    },
)

celery.autodiscover_tasks(
    [
        "apps.api.tasks.monitoring",
        "apps.api.tasks.briefing_generation",
    ]
)
