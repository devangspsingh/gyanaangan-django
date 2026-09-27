import logging
import threading
import requests
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BlogPost

logger = logging.getLogger(__name__)


def _send_revalidation_request(slug):
    """
    Sends a webhook request to Next.js /api/revalidate in a background thread.
    """
    webhook_url = getattr(settings, "FRONTEND_REVALIDATE_URL", None)
    secret_token = getattr(settings, "REVALIDATE_SECRET_TOKEN", None)

    if not webhook_url or not secret_token:
        logger.warning(
            "Frontend revalidation skipped: FRONTEND_REVALIDATE_URL or REVALIDATE_SECRET_TOKEN not configured."
        )
        return

    payload = {
        "secret": secret_token,
        "slug": slug,
        "path": f"/blog/{slug}",
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info("Successfully revalidated Next.js cache for blog slug: %s", slug)
        else:
            logger.warning(
                "Next.js revalidation failed for slug %s with status %s: %s",
                slug,
                response.status_code,
                response.text,
            )
    except requests.RequestException as e:
        logger.error("Failed to connect to Next.js revalidation endpoint: %s", str(e))


def trigger_blog_revalidation(slug):
    """
    Triggers revalidation in a background daemon thread after the DB transaction commits.
    """
    if not slug:
        return

    def _on_commit():
        thread = threading.Thread(
            target=_send_revalidation_request,
            args=(slug,),
            daemon=True,
            name=f"RevalidateBlog-{slug}",
        )
        thread.start()

    transaction.on_commit(_on_commit)


@receiver(post_save, sender=BlogPost)
def on_blog_post_saved(sender, instance, created, **kwargs):
    """
    Trigger Next.js ISR cache invalidation when a blog post is created or updated.
    """
    if instance.slug:
        trigger_blog_revalidation(instance.slug)


@receiver(post_delete, sender=BlogPost)
def on_blog_post_deleted(sender, instance, **kwargs):
    """
    Trigger Next.js ISR cache invalidation when a blog post is deleted.
    """
    if instance.slug:
        trigger_blog_revalidation(instance.slug)
