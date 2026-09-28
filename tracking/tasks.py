import logging
from .sync_service import sync_tracking_analytics

logger = logging.getLogger(__name__)

try:
    from celery import shared_task

    @shared_task(name="tracking.tasks.sync_analytics_task")
    def sync_analytics_task():
        """Periodic Celery task executing every 12 hours to incrementally sync tracking analytics."""
        logger.info("Executing Celery periodic analytics sync task...")
        result = sync_tracking_analytics()
        logger.info(f"Celery analytics sync completed: {result}")
        return result
except ImportError:
    def sync_analytics_task():
        logger.info("Celery not installed; executing direct analytics sync...")
        return sync_tracking_analytics()
