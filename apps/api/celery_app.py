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
        "apps.api.tasks.review_monitoring.*": {"queue": "monitoring"},
        "apps.api.tasks.social_monitoring.*": {"queue": "monitoring"},
        "apps.api.tasks.job_monitoring.*": {"queue": "monitoring"},
    },
    beat_schedule={
        # Website monitoring — daily at 2 AM UTC
        "monitor-websites-daily": {
            "task": "apps.api.tasks.monitoring.run_monitoring_cycle",
            "schedule": crontab(minute=0, hour=2),
        },
        # News monitoring — twice daily at 8 AM and 6 PM UTC
        "monitor-news-morning": {
            "task": "apps.api.tasks.monitoring.run_news_monitoring",
            "schedule": crontab(minute=0, hour=8),
        },
        "monitor-news-evening": {
            "task": "apps.api.tasks.monitoring.run_news_monitoring",
            "schedule": crontab(minute=0, hour=18),
        },
        # Job monitoring — daily at 3 AM UTC
        "monitor-jobs-daily": {
            "task": "apps.api.tasks.job_monitoring.run_job_monitoring_cycle",
            "schedule": crontab(minute=0, hour=3),
        },
        # Review scraping — weekly on Sundays at 4 AM UTC
        "scrape-reviews-weekly": {
            "task": "apps.api.tasks.review_monitoring.run_review_monitoring_cycle",
            "schedule": crontab(minute=0, hour=4, day_of_week="sunday"),
        },
        # Social monitoring — daily at 10 AM UTC
        "monitor-social-daily": {
            "task": "apps.api.tasks.social_monitoring.run_social_monitoring_cycle",
            "schedule": crontab(minute=0, hour=10),
        },
        # Briefing generation — weekly on Mondays
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
        "apps.api.tasks.review_monitoring",
        "apps.api.tasks.social_monitoring",
        "apps.api.tasks.job_monitoring",
    ]
)
