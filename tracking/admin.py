from datetime import timedelta
from urllib.parse import urlparse
from django.contrib import admin, messages
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone
from .models import Visitor, Session, Event, UserVisitor, BlogAnalytics, ResourceAnalytics
from .sync_service import sync_tracking_analytics

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('visitor_id', 'access_status', 'ip_address', 'device_type', 'os', 'browser','first_seen', 'last_seen')
    list_editable = ('access_status',)
    search_fields = ('visitor_id', 'ip_address', 'user_agent')
    readonly_fields = ('id', 'first_seen', 'last_seen', 'device_brand', 'device_model', 'os_version')
    list_filter = ('access_status',)

@admin.register(UserVisitor)
class UserVisitorAdmin(admin.ModelAdmin):
    list_display = ('user', 'visitor', 'last_used_at')
    search_fields = ('user__email', 'visitor__visitor_id')

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'visitor', 'user', 'start_time', 'last_activity', 'is_active', 'duration_seconds')
    list_filter = ('is_active', 'start_time')
    search_fields = ('visitor__visitor_id', 'user__email', 'user__username')
    readonly_fields = ('id', 'start_time', 'last_activity')

    def duration_seconds(self, obj):
        return f"{obj.duration:.2f}s"

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'url', 'get_user', 'get_ip', 'is_processed', 'timestamp')
    list_filter = ('is_processed', 'event_type', 'timestamp')
    search_fields = ('url', 'target_resource', 'session__user__username', 'session__visitor__ip_address', 'session__visitor__visitor_id')
    readonly_fields = ('id', 'timestamp')

    def get_user(self, obj):
        return obj.session.user
    get_user.short_description = 'User'
    get_user.admin_order_field = 'session__user'

    def get_ip(self, obj):
        return obj.session.visitor.ip_address
    get_ip.short_description = 'IP Address'
    get_ip.admin_order_field = 'session__visitor__ip_address'

    def session_link(self, obj):
        return obj.session


@admin.register(BlogAnalytics)
class BlogAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = "admin/tracking/bloganalytics/change_list.html"
    list_display = ('post_title', 'formatted_views', 'views_6h', 'views_24h', 'views_7d', 'last_processed_at')
    search_fields = ('post__title', 'post_slug')
    readonly_fields = ('post', 'post_slug', 'total_views', 'unique_visitors', 'last_processed_at', 'created_at')
    ordering = ('-total_views',)
    actions = ['trigger_sync_action']

    def changelist_view(self, request, extra_context=None):
        now = timezone.now()
        counts = Event.objects.filter(
            url__icontains="/blog/",
            timestamp__gte=now - timedelta(days=7),
        ).values("url").annotate(
            c_7d=Count("id"),
            c_24h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=24))),
            c_6h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=6))),
        )

        slug_6h = {}
        slug_24h = {}
        slug_7d = {}
        for item in counts:
            parts = urlparse(item["url"] or "").path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "blog":
                s = parts[1].split("?")[0].strip()
                if s:
                    slug_6h[s] = slug_6h.get(s, 0) + item["c_6h"]
                    slug_24h[s] = slug_24h.get(s, 0) + item["c_24h"]
                    slug_7d[s] = slug_7d.get(s, 0) + item["c_7d"]

        request._blog_views_6h = slug_6h
        request._blog_views_24h = slug_24h
        request._blog_views_7d = slug_7d

        extra_context = extra_context or {}
        extra_context["live_stats"] = {
            "views_6h": f"{sum(request._blog_views_6h.values()):,}",
            "views_24h": f"{sum(request._blog_views_24h.values()):,}",
            "views_7d": f"{sum(request._blog_views_7d.values()):,}",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        self._current_request = request
        return super().get_queryset(request)

    def post_title(self, obj):
        return obj.post.title if obj.post else obj.post_slug
    post_title.short_description = "Blog Post"

    def formatted_views(self, obj):
        return f"👁️ {obj.total_views:,}"
    formatted_views.short_description = "All Views"
    formatted_views.admin_order_field = "total_views"

    def views_6h(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_blog_views_6h", {}).get(obj.post_slug, 0)
        return f"{val:,}" if val else "-"
    views_6h.short_description = "⚡ Views (6h)"

    def views_24h(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_blog_views_24h", {}).get(obj.post_slug, 0)
        return f"{val:,}" if val else "-"
    views_24h.short_description = "📅 Views (24h)"

    def views_7d(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_blog_views_7d", {}).get(obj.post_slug, 0)
        return f"{val:,}" if val else "-"
    views_7d.short_description = "📈 Views (7d)"

    @admin.action(description="🔄 Run Incremental Sync (Process Unprocessed Events)")
    def trigger_sync_action(self, request, queryset):
        res = sync_tracking_analytics()
        self.message_user(
            request,
            f"✅ Sync complete! Processed {res['processed_events']:,} events in {res['duration_seconds']}s. "
            f"Updated {res['updated_blogs']} blog records, {res['updated_resources']} resource records.",
            level=messages.SUCCESS,
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-now/', self.admin_site.admin_view(self.sync_now_view), name='tracking_bloganalytics_sync'),
        ]
        return custom_urls + urls

    def sync_now_view(self, request):
        res = sync_tracking_analytics()
        messages.success(
            request,
            f"✅ Manual Sync Complete: Processed {res['processed_events']:,} events ({res['duration_seconds']}s). "
            f"Updated {res['updated_blogs']} blog posts, {res['updated_resources']} resources."
        )
        return redirect('admin:tracking_bloganalytics_changelist')


@admin.register(ResourceAnalytics)
class ResourceAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = "admin/tracking/resourceanalytics/change_list.html"
    list_display = (
        'resource_name',
        'resource_type',
        'formatted_views',
        'views_6h',
        'views_24h',
        'views_7d',
        'formatted_downloads',
        'downloads_6h',
        'downloads_24h',
        'downloads_7d',
        'formatted_engagement',
        'last_processed_at',
    )
    list_filter = ('resource_type', 'last_processed_at')
    search_fields = ('resource__name', 'resource_slug')
    readonly_fields = ('resource', 'resource_slug', 'resource_type', 'total_views', 'total_downloads', 'total_engagement', 'unique_visitors', 'last_processed_at', 'created_at')
    ordering = ('-total_engagement', '-total_views')
    actions = ['trigger_sync_action']

    def changelist_view(self, request, extra_context=None):
        now = timezone.now()

        # 1. Resource Page Views (7d, 24h, 6h in a single conditional aggregation query)
        res_counts = Event.objects.filter(
            url__icontains="/resources/",
            timestamp__gte=now - timedelta(days=7),
        ).values("url").annotate(
            c_7d=Count("id"),
            c_24h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=24))),
            c_6h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=6))),
        )

        res_6h = {}
        res_24h = {}
        res_7d = {}
        for item in res_counts:
            parts = urlparse(item["url"] or "").path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "resources":
                s = parts[1].split("?")[0].strip()
                if s:
                    res_6h[s] = res_6h.get(s, 0) + item["c_6h"]
                    res_24h[s] = res_24h.get(s, 0) + item["c_24h"]
                    res_7d[s] = res_7d.get(s, 0) + item["c_7d"]

        # 2. Resource File Downloads (7d, 24h, 6h in a single conditional aggregation query)
        dl_counts = Event.objects.filter(
            event_type="download",
            timestamp__gte=now - timedelta(days=7),
        ).exclude(target_resource__isnull=True).exclude(target_resource="").values("target_resource").annotate(
            c_7d=Count("id"),
            c_24h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=24))),
            c_6h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=6))),
        )

        dl_6h = {}
        dl_24h = {}
        dl_7d = {}
        for item in dl_counts:
            target = (item.get("target_resource") or "").split("?")[0].strip("/").split("/")[-1].strip()
            if target:
                dl_6h[target] = dl_6h.get(target, 0) + item["c_6h"]
                dl_24h[target] = dl_24h.get(target, 0) + item["c_24h"]
                dl_7d[target] = dl_7d.get(target, 0) + item["c_7d"]

        request._res_views_6h = res_6h
        request._res_views_24h = res_24h
        request._res_views_7d = res_7d
        request._res_dl_6h = dl_6h
        request._res_dl_24h = dl_24h
        request._res_dl_7d = dl_7d

        extra_context = extra_context or {}
        extra_context["live_stats"] = {
            "views_6h": f"{sum(request._res_views_6h.values()):,}",
            "views_24h": f"{sum(request._res_views_24h.values()):,}",
            "views_7d": f"{sum(request._res_views_7d.values()):,}",
            "downloads_6h": f"{sum(request._res_dl_6h.values()):,}",
            "downloads_24h": f"{sum(request._res_dl_24h.values()):,}",
            "downloads_7d": f"{sum(request._res_dl_7d.values()):,}",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        self._current_request = request
        return super().get_queryset(request)

    def resource_name(self, obj):
        return obj.resource.name if obj.resource else obj.resource_slug
    resource_name.short_description = "Resource"

    def formatted_views(self, obj):
        return f"👁️ {obj.total_views:,}"
    formatted_views.short_description = "All Views"
    formatted_views.admin_order_field = "total_views"

    def views_6h(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_res_views_6h", {}).get(obj.resource_slug, 0)
        return f"{val:,}" if val else "-"
    views_6h.short_description = "⚡ Views (6h)"

    def views_24h(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_res_views_24h", {}).get(obj.resource_slug, 0)
        return f"{val:,}" if val else "-"
    views_24h.short_description = "📅 Views (24h)"

    def views_7d(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_res_views_7d", {}).get(obj.resource_slug, 0)
        return f"{val:,}" if val else "-"
    views_7d.short_description = "📈 Views (7d)"

    def formatted_downloads(self, obj):
        return f"📥 {obj.total_downloads:,}"
    formatted_downloads.short_description = "All Downloads"
    formatted_downloads.admin_order_field = "total_downloads"

    def downloads_6h(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_res_dl_6h", {}).get(obj.resource_slug, 0)
        return f"{val:,}" if val else "-"
    downloads_6h.short_description = "⚡ DL (6h)"

    def downloads_24h(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_res_dl_24h", {}).get(obj.resource_slug, 0)
        return f"{val:,}" if val else "-"
    downloads_24h.short_description = "📅 DL (24h)"

    def downloads_7d(self, obj):
        req = getattr(self, "_current_request", None)
        val = getattr(req, "_res_dl_7d", {}).get(obj.resource_slug, 0)
        return f"{val:,}" if val else "-"
    downloads_7d.short_description = "📈 DL (7d)"

    def formatted_engagement(self, obj):
        return f"⚡ {obj.total_engagement:,}"
    formatted_engagement.short_description = "Engagement"
    formatted_engagement.admin_order_field = "total_engagement"

    @admin.action(description="🔄 Run Incremental Sync (Process Unprocessed Events)")
    def trigger_sync_action(self, request, queryset):
        res = sync_tracking_analytics()
        self.message_user(
            request,
            f"✅ Sync complete! Processed {res['processed_events']:,} events in {res['duration_seconds']}s. "
            f"Updated {res['updated_blogs']} blog records, {res['updated_resources']} resource records.",
            level=messages.SUCCESS,
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-now/', self.admin_site.admin_view(self.sync_now_view), name='tracking_resourceanalytics_sync'),
        ]
        return custom_urls + urls

    def sync_now_view(self, request):
        res = sync_tracking_analytics()
        messages.success(
            request,
            f"✅ Manual Sync Complete: Processed {res['processed_events']:,} events ({res['duration_seconds']}s). "
            f"Updated {res['updated_blogs']} blog posts, {res['updated_resources']} resources."
        )
        return redirect('admin:tracking_resourceanalytics_changelist')


