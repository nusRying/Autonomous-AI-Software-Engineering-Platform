"""
Celery worker configuration for long-running autonomous tasks.

This allows us to run audits in a separate process/container,
providing better isolation and persistence for agent operations.
"""
from celery import Celery
from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "audit_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.api.routes.audit", "app.api.routes.engineer"] # Register tasks here
)

# Optional configuration
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

if __name__ == "__main__":
    celery_app.start()
