import logging
import threading
import requests
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Resource, Subject, Course, Notification
from core.models import Banner

logger = logging.getLogger(__name__)


def _send_frontend_revalidation(paths):
    """
    Sends a webhook request to Next.js /api/revalidate for multiple paths.
    """
    webhook_url = getattr(settings, "FRONTEND_REVALIDATE_URL", None)
    secret_token = getattr(settings, "REVALIDATE_SECRET_TOKEN", None)

    if not webhook_url or not secret_token or not paths:
        logger.warning(
            "Frontend revalidation skipped: FRONTEND_REVALIDATE_URL or REVALIDATE_SECRET_TOKEN not configured."
        )
        return

    payload = {
        "secret": secret_token,
        "paths": list(paths),
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info("Successfully revalidated Next.js cache for paths: %s", paths)
        else:
            logger.warning(
                "Next.js revalidation failed for paths %s with status %s: %s",
                paths,
                response.status_code,
                response.text,
            )
    except requests.RequestException as e:
        logger.error("Failed to connect to Next.js revalidation endpoint: %s", str(e))


def _purge_cloudflare_cache(urls):
    """
    Purges Cloudflare Edge Cache for specified URLs.
    """
    zone_id = getattr(settings, "CLOUDFLARE_ZONE_ID", None)
    api_token = getattr(settings, "CLOUDFLARE_API_TOKEN", None)

    if not zone_id or not api_token or not urls:
        logger.info(
            "Cloudflare edge purge skipped: CLOUDFLARE_ZONE_ID or CLOUDFLARE_API_TOKEN not configured."
        )
        return

    purge_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {"files": list(urls)}

    try:
        response = requests.post(purge_url, json=payload, headers=headers, timeout=5)
        res_data = response.json() if response.content else {}
        if response.status_code == 200 and res_data.get("success"):
            logger.info("Successfully purged Cloudflare edge cache for: %s", urls)
        else:
            logger.warning(
                "Cloudflare edge purge returned status %s: %s",
                response.status_code,
                res_data.get("errors") or response.text,
            )
    except requests.RequestException as e:
        logger.error("Failed to connect to Cloudflare Purge API: %s", str(e))


def _run_all_revalidations(paths, urls):
    """
    Executes both Next.js revalidation and Cloudflare edge cache purge in the background.
    """
    _send_frontend_revalidation(paths)
    _purge_cloudflare_cache(urls)


def trigger_paths_revalidation(paths):
    """
    Triggers revalidation in a background daemon thread after DB transaction commit.
    """
    if not paths:
        return

    clean_paths = sorted(list(set(p for p in paths if p)))
    clean_urls = [f"https://gyanaangan.in{p}" for p in clean_paths]

    def _on_commit():
        thread = threading.Thread(
            target=_run_all_revalidations,
            args=(clean_paths, clean_urls),
            daemon=True,
            name=f"RevalidateCourses-{len(clean_paths)}",
        )
        thread.start()

    transaction.on_commit(_on_commit)


@receiver(post_save, sender=Resource)
def update_subject_last_resource_updated(sender, instance, **kwargs):
    if instance.subject:
        try:
            # Update subject's last_resource_updated timestamp directly in DB
            Subject.objects.filter(pk=instance.subject.pk).update(
                last_resource_updated_at=instance.updated_at
            )
        except Exception as e:
            logger.warning("Could not update subject last_resource_updated_at: %s", e)


@receiver(post_save, sender=Resource)
@receiver(post_delete, sender=Resource)
def on_resource_changed(sender, instance, **kwargs):
    paths = ["/", "/resources"]
    if instance.slug:
        paths.append(f"/resources/{instance.slug}")
    if instance.subject and instance.subject.slug:
        paths.append(f"/subjects/{instance.subject.slug}")
        if instance.subject.course and instance.subject.course.slug:
            paths.append(f"/{instance.subject.course.slug}")
    trigger_paths_revalidation(paths)


@receiver(post_save, sender=Subject)
@receiver(post_delete, sender=Subject)
def on_subject_changed(sender, instance, **kwargs):
    paths = ["/", "/subjects"]
    if instance.slug:
        paths.append(f"/subjects/{instance.slug}")
    if instance.course and instance.course.slug:
        paths.append(f"/{instance.course.slug}")
    trigger_paths_revalidation(paths)


@receiver(post_save, sender=Course)
@receiver(post_delete, sender=Course)
def on_course_changed(sender, instance, **kwargs):
    paths = ["/", "/courses"]
    if instance.slug:
        paths.append(f"/{instance.slug}")
    trigger_paths_revalidation(paths)


@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def on_notification_changed(sender, instance, **kwargs):
    trigger_paths_revalidation(["/"])


@receiver(post_save, sender=Banner)
@receiver(post_delete, sender=Banner)
def on_banner_changed(sender, instance, **kwargs):
    trigger_paths_revalidation(["/"])
