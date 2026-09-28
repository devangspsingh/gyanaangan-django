from datetime import timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from django.db.models import Sum, Count
from django.utils import timezone
from blog.models import BlogPost
from courses.models import Resource
from tracking.models import Event, BlogAnalytics, ResourceAnalytics


def get_blog_views_analytics(
    slug: Optional[str] = None,
    time_window: str = "all",
    limit: int = 15,
) -> Dict[str, Any]:
    """
    Retrieve blog view metrics for a specific post (including live 6h, 24h, 7d breakdown),
    or top-performing blog posts ranked by views for a given time window.
    """
    now = timezone.now()

    if slug:
        post = (
            BlogPost.objects.filter(slug=slug).first()
            or BlogPost.objects.filter(id=slug if slug.isdigit() else None).first()
        )
        if not post:
            return {"error": f"Blog post with identifier '{slug}' not found."}

        analytics = getattr(post, "tracking_analytics", None)

        # Live calculation of 6h, 24h, 7d views
        events_7d = Event.objects.filter(
            url__icontains=f"/blog/{post.slug}",
            timestamp__gte=now - timedelta(days=7),
        )
        views_6h = events_7d.filter(timestamp__gte=now - timedelta(hours=6)).count()
        views_24h = events_7d.filter(timestamp__gte=now - timedelta(hours=24)).count()
        views_7d = events_7d.count()

        return {
            "title": post.title,
            "slug": post.slug,
            "category": post.category.name if post.category else None,
            "status": post.status,
            "publish_date": post.publish_date.strftime("%Y-%m-%d %H:%M") if post.publish_date else None,
            "total_views": post.view_count or (analytics.total_views if analytics else 0),
            "views_last_6h": views_6h,
            "views_last_24h": views_24h,
            "views_last_7d": views_7d,
            "unique_visitors": analytics.unique_visitors if analytics else 0,
            "last_processed_at": analytics.last_processed_at.strftime("%Y-%m-%d %H:%M") if analytics and analytics.last_processed_at else None,
        }

    # Aggregate top posts (all-time or live window)
    limit = max(1, min(limit, 50))

    if time_window in ("6h", "24h", "7d"):
        hours = 6 if time_window == "6h" else (24 if time_window == "24h" else 168)
        counts = (
            Event.objects.filter(
                url__icontains="/blog/",
                timestamp__gte=now - timedelta(hours=hours),
            )
            .values("url")
            .annotate(views=Count("id"))
            .order_by("-views")
        )
        slug_views = {}
        for item in counts:
            parts = urlparse(item["url"] or "").path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "blog":
                s = parts[1].split("?")[0].strip()
                if s:
                    slug_views[s] = slug_views.get(s, 0) + item["views"]

        # Sort and retrieve post details
        sorted_slugs = sorted(slug_views.items(), key=lambda x: x[1], reverse=True)[:limit]
        results = []
        for s, count in sorted_slugs:
            p = BlogPost.objects.filter(slug=s).first()
            if p:
                results.append({
                    "id": p.id,
                    "title": p.title,
                    "slug": p.slug,
                    "category": p.category.name if p.category else None,
                    f"views_last_{time_window}": count,
                    "all_time_views": p.view_count or 0,
                })

        return {
            "time_window": time_window,
            "total_window_views": sum(slug_views.values()),
            "top_posts_count": len(results),
            "top_posts": results,
        }

    # Default: All-time top posts from synced view_count
    top_posts = BlogPost.objects.select_related("category").order_by("-view_count")[:limit]
    total_views = BlogPost.objects.aggregate(total=Sum("view_count"))["total"] or 0
    total_posts = BlogPost.objects.count()

    results = []
    for p in top_posts:
        results.append({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "category": p.category.name if p.category else None,
            "status": p.status,
            "total_views": p.view_count or 0,
            "publish_date": p.publish_date.strftime("%Y-%m-%d") if p.publish_date else None,
        })

    return {
        "time_window": "all",
        "summary": {
            "total_posts": total_posts,
            "total_views_recorded": total_views,
            "top_posts_count": len(results),
        },
        "top_posts": results,
    }


def get_resource_views_analytics(
    slug: Optional[str] = None,
    resource_type: Optional[str] = None,
    time_window: str = "all",
    limit: int = 15,
) -> Dict[str, Any]:
    """
    Retrieve views, downloads, and engagement metrics for resources (including live 6h, 24h, 7d breakdown).
    """
    now = timezone.now()

    if slug:
        res = (
            Resource.objects.filter(slug=slug).first()
            or Resource.objects.filter(id=slug if slug.isdigit() else None).first()
        )
        if not res:
            return {"error": f"Resource with identifier '{slug}' not found."}

        analytics = getattr(res, "tracking_analytics", None)

        # Live calculation of 6h, 24h, 7d views and downloads
        res_events = Event.objects.filter(
            url__icontains=f"/resources/{res.slug}",
            timestamp__gte=now - timedelta(days=7),
        )
        views_6h = res_events.filter(timestamp__gte=now - timedelta(hours=6)).count()
        views_24h = res_events.filter(timestamp__gte=now - timedelta(hours=24)).count()
        views_7d = res_events.count()

        dl_events = Event.objects.filter(
            event_type="download",
            target_resource__icontains=res.slug,
            timestamp__gte=now - timedelta(days=7),
        )
        downloads_6h = dl_events.filter(timestamp__gte=now - timedelta(hours=6)).count()
        downloads_24h = dl_events.filter(timestamp__gte=now - timedelta(hours=24)).count()
        downloads_7d = dl_events.count()

        return {
            "name": res.name,
            "slug": res.slug,
            "resource_type": res.resource_type,
            "subject": res.subject.name if res.subject else None,
            "total_views": analytics.total_views if analytics else 0,
            "total_downloads": analytics.total_downloads if analytics else 0,
            "total_engagement": analytics.total_engagement if analytics else 0,
            "views_last_6h": views_6h,
            "views_last_24h": views_24h,
            "views_last_7d": views_7d,
            "downloads_last_6h": downloads_6h,
            "downloads_last_24h": downloads_24h,
            "downloads_last_7d": downloads_7d,
            "unique_visitors": analytics.unique_visitors if analytics else 0,
            "last_processed_at": analytics.last_processed_at.strftime("%Y-%m-%d %H:%M") if analytics and analytics.last_processed_at else None,
        }

    # Aggregate top resources
    limit = max(1, min(limit, 50))
    qs = ResourceAnalytics.objects.select_related("resource", "resource__subject")
    if resource_type:
        qs = qs.filter(resource_type__iexact=resource_type)

    top_analytics = qs.order_by("-total_engagement", "-total_views")[:limit]

    aggregates = ResourceAnalytics.objects.aggregate(
        total_views=Sum("total_views"),
        total_downloads=Sum("total_downloads"),
        total_engagement=Sum("total_engagement"),
    )

    results = []
    for item in top_analytics:
        res = item.resource
        results.append({
            "name": res.name if res else item.resource_slug,
            "slug": item.resource_slug,
            "resource_type": item.resource_type,
            "subject": res.subject.name if res and res.subject else None,
            "views": item.total_views,
            "downloads": item.total_downloads,
            "total_engagement": item.total_engagement,
            "last_processed_at": item.last_processed_at.strftime("%Y-%m-%d %H:%M") if item.last_processed_at else None,
        })

    return {
        "summary": {
            "total_tracked_resources": ResourceAnalytics.objects.count(),
            "total_views_recorded": aggregates["total_views"] or 0,
            "total_downloads_recorded": aggregates["total_downloads"] or 0,
            "total_engagement_recorded": aggregates["total_engagement"] or 0,
        },
        "top_resources": results,
    }
