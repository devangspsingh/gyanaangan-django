import logging
import time
from urllib.parse import urlparse
from django.db import models
from django.db.models import Count, F
from django.utils import timezone
from blog.models import BlogPost
from courses.models import Resource
from .models import Event, BlogAnalytics, ResourceAnalytics

logger = logging.getLogger(__name__)


def sync_tracking_analytics() -> dict:
    """
    Incrementally syncs unprocessed tracking.Event records into BlogAnalytics
    and ResourceAnalytics models, and updates BlogPost.view_count.
    
    Uses direct database aggregations and marks processed events with is_processed=True.
    Subsequent runs process only newly arrived events in milliseconds.
    """
    start_time = time.time()
    unprocessed_qs = Event.objects.filter(is_processed=False)
    unprocessed_count = unprocessed_qs.count()

    if unprocessed_count == 0:
        return {
            "processed_events": 0,
            "updated_blogs": 0,
            "updated_resources": 0,
            "duration_seconds": 0.0,
        }

    # Lock processing boundary by timestamp to ensure safety with concurrent incoming events
    max_timestamp = unprocessed_qs.aggregate(max_ts=models.Max("timestamp"))["max_ts"]
    if not max_timestamp:
        max_timestamp = timezone.now()

    current_run_qs = Event.objects.filter(is_processed=False, timestamp__lte=max_timestamp)
    now = timezone.now()

    # 1. Aggregate Blog Views
    blog_url_counts = (
        current_run_qs.filter(url__icontains="/blog/")
        .values("url")
        .annotate(views=Count("id"))
    )
    blog_slug_views = {}
    for item in blog_url_counts:
        url_str = item.get("url") or ""
        path_parts = urlparse(url_str).path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "blog":
            slug = path_parts[1].split("?")[0].strip()
            if slug:
                blog_slug_views[slug] = blog_slug_views.get(slug, 0) + item["views"]

    total_blog_updates = 0
    for slug, view_count in blog_slug_views.items():
        post = BlogPost.objects.filter(slug=slug).first()
        if post:
            analytics, _ = BlogAnalytics.objects.get_or_create(
                post=post,
                defaults={"post_slug": post.slug},
            )
            BlogAnalytics.objects.filter(id=analytics.id).update(
                total_views=F("total_views") + view_count,
                last_processed_at=now,
            )
            BlogPost.objects.filter(id=post.id).update(
                view_count=F("view_count") + view_count
            )
            total_blog_updates += 1

    # 2. Aggregate Resource Page Views
    res_url_counts = (
        current_run_qs.filter(url__icontains="/resources/")
        .values("url")
        .annotate(views=Count("id"))
    )
    res_slug_views = {}
    for item in res_url_counts:
        url_str = item.get("url") or ""
        path_parts = urlparse(url_str).path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "resources":
            slug = path_parts[1].split("?")[0].strip()
            if slug:
                res_slug_views[slug] = res_slug_views.get(slug, 0) + item["views"]

    total_resource_updates = 0
    for slug, view_count in res_slug_views.items():
        res = Resource.objects.filter(slug=slug).first()
        if res:
            analytics, _ = ResourceAnalytics.objects.get_or_create(
                resource=res,
                defaults={
                    "resource_slug": res.slug,
                    "resource_type": res.resource_type or "",
                },
            )
            ResourceAnalytics.objects.filter(id=analytics.id).update(
                total_views=F("total_views") + view_count,
                total_engagement=F("total_engagement") + view_count,
                last_processed_at=now,
            )
            total_resource_updates += 1

    # 3. Aggregate Resource File Downloads
    dl_counts = (
        current_run_qs.filter(event_type="download")
        .exclude(target_resource__isnull=True)
        .exclude(target_resource="")
        .values("target_resource")
        .annotate(downloads=Count("id"))
    )
    res_slug_dls = {}
    for item in dl_counts:
        raw_target = item.get("target_resource") or ""
        slug = raw_target.split("?")[0].strip("/").split("/")[-1].strip()
        if slug:
            res_slug_dls[slug] = res_slug_dls.get(slug, 0) + item["downloads"]

    for slug, dl_count in res_slug_dls.items():
        res = Resource.objects.filter(slug=slug).first()
        if res:
            analytics, _ = ResourceAnalytics.objects.get_or_create(
                resource=res,
                defaults={
                    "resource_slug": res.slug,
                    "resource_type": res.resource_type or "",
                },
            )
            ResourceAnalytics.objects.filter(id=analytics.id).update(
                total_downloads=F("total_downloads") + dl_count,
                total_engagement=F("total_engagement") + dl_count,
                last_processed_at=now,
            )
            total_resource_updates += 1

    # 4. Mark processed events in bulk
    processed_count = current_run_qs.update(is_processed=True)
    elapsed = round(time.time() - start_time, 2)

    logger.info(
        f"Tracking sync finished: {processed_count} events marked processed, "
        f"{total_blog_updates} blog posts, {total_resource_updates} resources in {elapsed}s"
    )

    return {
        "processed_events": processed_count,
        "updated_blogs": total_blog_updates,
        "updated_resources": total_resource_updates,
        "duration_seconds": elapsed,
    }
