import logging
from datetime import timedelta
from urllib.parse import urlparse

from django.contrib import admin, messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from tracking.models import Event
from .models import BlogAnalytics, BlogPost, Category

logger = logging.getLogger(__name__)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    change_list_template = "admin/blog/change_list.html"

    list_display = (
        "title",
        "author",
        "category",
        "status",
        "publish_date",
        "real_views_badge",
        "analytics_action",
    )
    list_filter = ("status", "publish_date", "author", "is_featured", "category")
    search_fields = ("title", "content", "slug")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)
    date_hierarchy = "publish_date"
    ordering = ["-publish_date", "-created_at"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "slug",
                    "author",
                    "category",
                    "content",
                    "excerpt",
                    "featured_image",
                )
            },
        ),
        (
            "SEO Settings",
            {
                "fields": ("meta_description", "keywords", "og_image"),
            },
        ),
        (
            "Publication Settings",
            {
                "fields": (
                    "status",
                    "publish_date",
                    "is_featured",
                    "sticky_post",
                    "view_count",
                    "reading_time",
                ),
            },
        ),
    )

    @admin.display(description="Total Views", ordering="view_count")
    def real_views_badge(self, obj):
        views = obj.view_count or 0
        return format_html(
            '<a href="{}" style="font-weight: 700; color: #48bb78; text-decoration: none;" title="Open detailed metrics">'
            '👁️ {:,}'
            '</a>',
            reverse("admin:blog_analytics_detail", args=[obj.slug]),
            views,
        )

    @admin.display(description="Metrics")
    def analytics_action(self, obj):
        return format_html(
            '<a class="button" style="padding: 3px 8px; font-size: 11px; background: #3182ce; color: #fff;" href="{}">'
            '📈 Stats'
            '</a>',
            reverse("admin:blog_analytics_detail", args=[obj.slug]),
        )


@admin.register(BlogAnalytics)
class BlogAnalyticsAdmin(admin.ModelAdmin):
    """
    Dedicated Admin Controller for Blog Views, Metrics, Readers, and Device Headers.
    """

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "",
                self.admin_site.admin_view(self.dashboard_view),
                name="blog_analytics",
            ),
            path(
                "sync/",
                self.admin_site.admin_view(self.sync_views),
                name="blog_analytics_sync",
            ),
            path(
                "<path:slug>/",
                self.admin_site.admin_view(self.detail_view),
                name="blog_analytics_detail",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        return self.dashboard_view(request)

    def dashboard_view(self, request):
        time_filter = request.GET.get("range", "all")
        query = request.GET.get("q", "").strip()

        now = timezone.now()
        if time_filter == "today":
            since = now - timedelta(hours=24)
        elif time_filter == "7d":
            since = now - timedelta(days=7)
        elif time_filter == "30d":
            since = now - timedelta(days=30)
        else:
            since = None

        event_qs = Event.objects.filter(url__icontains="/blog/")
        if since:
            event_qs = event_qs.filter(timestamp__gte=since)

        # High-level Metrics
        total_views = event_qs.count()
        unique_visitors = (
            event_qs.values("session__visitor_id").distinct().count()
        )
        views_24h = Event.objects.filter(
            url__icontains="/blog/", timestamp__gte=now - timedelta(hours=24)
        ).count()
        views_7d = Event.objects.filter(
            url__icontains="/blog/", timestamp__gte=now - timedelta(days=7)
        ).count()

        # Browser Breakdown
        raw_browsers = list(
            event_qs.exclude(session__visitor__browser__isnull=True)
            .values("session__visitor__browser")
            .annotate(count=Count("id"))
            .order_by("-count")[:6]
        )
        browsers = []
        for b in raw_browsers:
            count = b["count"]
            pct = round((count / total_views * 100), 1) if total_views else 0
            browsers.append(
                {"name": b["session__visitor__browser"] or "Unknown", "count": count, "pct": pct}
            )

        # OS Breakdown
        raw_os = list(
            event_qs.exclude(session__visitor__os__isnull=True)
            .values("session__visitor__os")
            .annotate(count=Count("id"))
            .order_by("-count")[:6]
        )
        os_list = []
        for o in raw_os:
            count = o["count"]
            pct = round((count / total_views * 100), 1) if total_views else 0
            os_list.append(
                {"name": o["session__visitor__os"] or "Unknown", "count": count, "pct": pct}
            )

        # Device Types Breakdown
        raw_devices = list(
            event_qs.values("session__visitor__device_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        devices = []
        for d in raw_devices:
            raw_name = d["session__visitor__device_type"]
            name = raw_name if raw_name else "Desktop/Unknown"
            count = d["count"]
            pct = round((count / total_views * 100), 1) if total_views else 0
            devices.append({"name": name, "count": count, "pct": pct})

        # Aggregated Blog Post Performance
        url_counts = (
            event_qs.values("url")
            .annotate(views=Count("id"), visitors=Count("session__visitor_id", distinct=True))
        )
        slug_stats = {}
        for item in url_counts:
            url = item.get("url") or ""
            path_str = urlparse(url).path
            if path_str.startswith("/blog/"):
                parts = path_str.strip("/").split("/")
                if len(parts) >= 2 and parts[0] == "blog":
                    slug = parts[1]
                    if slug not in slug_stats:
                        slug_stats[slug] = {"views": 0, "visitors": 0}
                    slug_stats[slug]["views"] += item["views"]
                    slug_stats[slug]["visitors"] += item["visitors"]

        posts_qs = BlogPost.objects.select_related("category", "author").all()
        if query:
            posts_qs = posts_qs.filter(Q(title__icontains=query) | Q(slug__icontains=query))

        blog_list = []
        for post in posts_qs:
            st = slug_stats.get(post.slug, {"views": 0, "visitors": 0})
            blog_list.append(
                {
                    "post": post,
                    "views": st["views"],
                    "visitors": st["visitors"],
                    "all_time_views": post.view_count or 0,
                }
            )

        # Sort blog list by period views descending
        blog_list.sort(key=lambda x: (x["views"], x["all_time_views"]), reverse=True)

        context = {
            **self.admin_site.each_context(request),
            "title": "Blog Performance & Analytics",
            "time_filter": time_filter,
            "query": query,
            "total_views": f"{total_views:,}",
            "unique_visitors": f"{unique_visitors:,}",
            "views_24h": f"{views_24h:,}",
            "views_7d": f"{views_7d:,}",
            "browsers": browsers,
            "os_list": os_list,
            "devices": devices,
            "blog_list": blog_list,
        }
        return render(request, "admin/blog/dashboard.html", context)

    def detail_view(self, request, slug):
        post = get_object_or_404(BlogPost.objects.select_related("category", "author"), slug=slug)

        now = timezone.now()
        post_events = Event.objects.filter(url__icontains=f"/blog/{post.slug}").select_related(
            "session__visitor", "session__user"
        )

        total_views = post_events.count()
        unique_visitors = post_events.values("session__visitor_id").distinct().count()
        views_24h = post_events.filter(timestamp__gte=now - timedelta(hours=24)).count()
        views_7d = post_events.filter(timestamp__gte=now - timedelta(days=7)).count()

        # 14-day daily views timeline
        daily_views = []
        max_daily = 1
        for i in range(13, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            cnt = post_events.filter(timestamp__gte=day_start, timestamp__lt=day_end).count()
            if cnt > max_daily:
                max_daily = cnt
            daily_views.append({"date": day_start.strftime("%b %d"), "count": cnt})

        for day in daily_views:
            day["height_pct"] = max(4, round((day["count"] / max_daily) * 100))

        # Top Browsers for this post
        raw_browsers = list(
            post_events.exclude(session__visitor__browser__isnull=True)
            .values("session__visitor__browser")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        browsers = []
        for b in raw_browsers:
            count = b["count"]
            pct = round((count / total_views * 100), 1) if total_views else 0
            browsers.append(
                {"name": b["session__visitor__browser"] or "Unknown", "count": count, "pct": pct}
            )

        # Top OS for this post
        raw_os = list(
            post_events.exclude(session__visitor__os__isnull=True)
            .values("session__visitor__os")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        os_list = []
        for o in raw_os:
            count = o["count"]
            pct = round((count / total_views * 100), 1) if total_views else 0
            os_list.append(
                {"name": o["session__visitor__os"] or "Unknown", "count": count, "pct": pct}
            )

        # Device Types for this post
        raw_devices = list(
            post_events.values("session__visitor__device_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        devices = []
        for d in raw_devices:
            name = d["session__visitor__device_type"] or "Desktop/Unknown"
            count = d["count"]
            pct = round((count / total_views * 100), 1) if total_views else 0
            devices.append({"name": name, "count": count, "pct": pct})

        # Recent 50 Visitor Logs
        recent_logs = []
        for ev in post_events.order_by("-timestamp")[:50]:
            v = getattr(ev.session, "visitor", None)
            device_str = (
                f"{v.device_brand or ''} {v.device_model or ''}".strip()
                if v
                else ""
            ) or (v.device_type if v else "Desktop")

            recent_logs.append(
                {
                    "timestamp": ev.timestamp,
                    "ip_address": v.ip_address if v and v.ip_address else "N/A",
                    "browser": v.browser if v and v.browser else "Unknown",
                    "os": v.os if v and v.os else "Unknown",
                    "device": device_str,
                    "user_agent": v.user_agent if v and v.user_agent else "N/A",
                    "user": ev.session.user.username if ev.session.user else "Anonymous",
                }
            )

        context = {
            **self.admin_site.each_context(request),
            "title": f"Metrics: {post.title}",
            "post": post,
            "total_views": f"{total_views:,}",
            "unique_visitors": f"{unique_visitors:,}",
            "views_24h": f"{views_24h:,}",
            "views_7d": f"{views_7d:,}",
            "daily_views": daily_views,
            "browsers": browsers,
            "os_list": os_list,
            "devices": devices,
            "recent_logs": recent_logs,
        }
        return render(request, "admin/blog/post_analytics.html", context)

    def sync_views(self, request):
        if request.method == "POST":
            counts_by_url = (
                Event.objects.filter(url__icontains="/blog/")
                .values("url")
                .annotate(views=Count("id"))
            )
            slug_views = {}
            for item in counts_by_url:
                url = item.get("url") or ""
                path_str = urlparse(url).path
                if path_str.startswith("/blog/"):
                    parts = path_str.strip("/").split("/")
                    if len(parts) >= 2 and parts[0] == "blog":
                        slug = parts[1]
                        slug_views[slug] = slug_views.get(slug, 0) + item["views"]

            updated_count = 0
            for slug, count in slug_views.items():
                updated = BlogPost.objects.filter(slug=slug).update(view_count=count)
                if updated:
                    updated_count += updated

            messages.success(
                request,
                f"Successfully synced view counts for {updated_count} blog posts from tracking events!",
            )
        return redirect("admin:blog_analytics")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
