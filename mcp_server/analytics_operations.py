from typing import Optional, Dict, Any, List
from django.db.models import Sum
from blog.models import BlogPost
from courses.models import Resource
from tracking.models import BlogAnalytics, ResourceAnalytics


def get_blog_views_analytics(slug: Optional[str] = None, limit: int = 15) -> Dict[str, Any]:
    """
    Retrieve blog view metrics for a specific post, or top-performing blog posts ranked by views.
    """
    if slug:
        post = (
            BlogPost.objects.filter(slug=slug).first()
            or BlogPost.objects.filter(id=slug if slug.isdigit() else None).first()
        )
        if not post:
            return {"error": f"Blog post with identifier '{slug}' not found."}

        analytics = getattr(post, "tracking_analytics", None)
        return {
            "title": post.title,
            "slug": post.slug,
            "category": post.category.name if post.category else None,
            "status": post.status,
            "publish_date": post.publish_date.strftime("%Y-%m-%d %H:%M") if post.publish_date else None,
            "view_count": post.view_count or (analytics.total_views if analytics else 0),
            "unique_visitors": analytics.unique_visitors if analytics else 0,
            "last_processed_at": analytics.last_processed_at.strftime("%Y-%m-%d %H:%M") if analytics and analytics.last_processed_at else None,
        }

    # Aggregate top posts
    limit = max(1, min(limit, 50))
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
            "view_count": p.view_count or 0,
            "publish_date": p.publish_date.strftime("%Y-%m-%d") if p.publish_date else None,
        })

    return {
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
    limit: int = 15
) -> Dict[str, Any]:
    """
    Retrieve views, downloads, and engagement metrics for resources (study materials, pyqs, notes).
    """
    if slug:
        res = (
            Resource.objects.filter(slug=slug).first()
            or Resource.objects.filter(id=slug if slug.isdigit() else None).first()
        )
        if not res:
            return {"error": f"Resource with identifier '{slug}' not found."}

        analytics = getattr(res, "tracking_analytics", None)
        return {
            "name": res.name,
            "slug": res.slug,
            "resource_type": res.resource_type,
            "subject": res.subject.name if res.subject else None,
            "total_views": analytics.total_views if analytics else 0,
            "total_downloads": analytics.total_downloads if analytics else 0,
            "total_engagement": analytics.total_engagement if analytics else 0,
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
