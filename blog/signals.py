import logging
import threading
import requests
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BlogPost, Category
from api.cache_utils import bump_cache_version

logger = logging.getLogger(__name__)


def _send_frontend_revalidation(slug):
    """
    Sends a webhook request to Next.js /api/revalidate.
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


def _purge_cloudflare_cache(slug):
    """
    Purges Cloudflare Edge Cache for the specific blog post and the blog index.
    """
    zone_id = getattr(settings, "CLOUDFLARE_ZONE_ID", None)
    api_token = getattr(settings, "CLOUDFLARE_API_TOKEN", None)

    if not zone_id or not api_token:
        logger.info(
            "Cloudflare edge purge skipped: CLOUDFLARE_ZONE_ID or CLOUDFLARE_API_TOKEN not configured."
        )
        return

    purge_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    files = [
        f"https://gyanaangan.in/blog/{slug}",
        "https://gyanaangan.in/blog",
    ]
    payload = {"files": files}

    try:
        response = requests.post(purge_url, json=payload, headers=headers, timeout=5)
        res_data = response.json() if response.content else {}
        if response.status_code == 200 and res_data.get("success"):
            logger.info("Successfully purged Cloudflare edge cache for: %s", files)
        else:
            logger.warning(
                "Cloudflare edge purge returned status %s: %s",
                response.status_code,
                res_data.get("errors") or response.text,
            )
    except requests.RequestException as e:
        logger.error("Failed to connect to Cloudflare Purge API: %s", str(e))


def _run_all_revalidations(slug):
    """
    Executes both Next.js revalidation and Cloudflare edge cache purge in the background.
    """
    _send_frontend_revalidation(slug)
    _purge_cloudflare_cache(slug)


def trigger_blog_revalidation(slug):
    """
    Triggers revalidation in a background daemon thread after the DB transaction commits.
    """
    if not slug:
        return

    def _on_commit():
        thread = threading.Thread(
            target=_run_all_revalidations,
            args=(slug,),
            daemon=True,
            name=f"RevalidateBlog-{slug}",
        )
        thread.start()

    transaction.on_commit(_on_commit)


@receiver(post_save, sender=BlogPost)
def on_blog_post_saved(sender, instance, created, **kwargs):
    """
    Trigger Next.js ISR cache invalidation, Cloudflare edge purge, and Redis cache invalidation when a blog post is saved.
    """
    bump_cache_version("blog")
    if instance.slug:
        trigger_blog_revalidation(instance.slug)


@receiver(post_delete, sender=BlogPost)
def on_blog_post_deleted(sender, instance, **kwargs):
    """
    Trigger Next.js ISR cache invalidation, Cloudflare edge purge, and Redis cache invalidation when a blog post is deleted.
    """
    bump_cache_version("blog")
    if instance.slug:
        trigger_blog_revalidation(instance.slug)


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def on_category_changed(sender, instance, **kwargs):
    bump_cache_version("categories")
    bump_cache_version("blog")

