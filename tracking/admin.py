from datetime import timedelta
from urllib.parse import urlparse
from django.contrib import admin, messages
from django.db.models import Count, Q, Case, When, Value, IntegerField
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone
from .models import Visitor, Session, Event, UserVisitor, BlogAnalytics, ResourceAnalytics
from .sync_service import sync_tracking_analytics
from .tasks import sync_analytics_task

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
    list_display = (
        'post_title',
        'published_at',
        'views_30d',
        'views_7d',
        'views_24h',
        'views_6h',
        'formatted_views',
        'last_processed_at',
    )
    search_fields = ('post__title', 'post_slug')
    readonly_fields = ('post', 'post_slug', 'total_views', 'unique_visitors', 'last_processed_at', 'created_at')
    actions = ['trigger_sync_action']

    def get_queryset(self, request):
        now = timezone.now()
        counts = Event.objects.filter(
            url__icontains="/blog/",
            timestamp__gte=now - timedelta(days=30),
        ).values("url").annotate(
            c_30d=Count("id"),
            c_7d=Count("id", filter=Q(timestamp__gte=now - timedelta(days=7))),
            c_24h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=24))),
            c_6h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=6))),
        )

        s_6h, s_24h, s_7d, s_30d = {}, {}, {}, {}
        for item in counts:
            parts = urlparse(item["url"] or "").path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "blog":
                s = parts[1].split("?")[0].strip()
                if s:
                    s_6h[s] = s_6h.get(s, 0) + item["c_6h"]
                    s_24h[s] = s_24h.get(s, 0) + item["c_24h"]
                    s_7d[s] = s_7d.get(s, 0) + item["c_7d"]
                    s_30d[s] = s_30d.get(s, 0) + item["c_30d"]

        request._blog_totals = {
            "views_6h": sum(s_6h.values()),
            "views_24h": sum(s_24h.values()),
            "views_7d": sum(s_7d.values()),
            "views_30d": sum(s_30d.values()),
        }

        w_6h = [When(post_slug=s, then=Value(c)) for s, c in s_6h.items()]
        w_24h = [When(post_slug=s, then=Value(c)) for s, c in s_24h.items()]
        w_7d = [When(post_slug=s, then=Value(c)) for s, c in s_7d.items()]
        w_30d = [When(post_slug=s, then=Value(c)) for s, c in s_30d.items()]

        return self.model._default_manager.get_queryset().select_related("post").annotate(
            v_6h=Case(*w_6h, default=Value(0), output_field=IntegerField()) if w_6h else Value(0),
            v_24h=Case(*w_24h, default=Value(0), output_field=IntegerField()) if w_24h else Value(0),
            v_7d=Case(*w_7d, default=Value(0), output_field=IntegerField()) if w_7d else Value(0),
            v_30d=Case(*w_30d, default=Value(0), output_field=IntegerField()) if w_30d else Value(0),
        )

    def get_ordering(self, request):
        if request.GET.get('o'):
            return super().get_ordering(request)
        return ['-v_30d', '-total_views']

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        if hasattr(response, "context_data") and response.context_data:
            totals = getattr(request, "_blog_totals", {})
            response.context_data["live_stats"] = {
                "views_6h": f"{totals.get('views_6h', 0):,}",
                "views_24h": f"{totals.get('views_24h', 0):,}",
                "views_7d": f"{totals.get('views_7d', 0):,}",
                "views_30d": f"{totals.get('views_30d', 0):,}",
            }
        return response

    def post_title(self, obj):
        return obj.post.title if obj.post else obj.post_slug
    post_title.short_description = "Blog Post"

    def published_at(self, obj):
        if obj.post and obj.post.publish_date:
            return obj.post.publish_date.strftime("%Y-%m-%d")
        return "-"
    published_at.short_description = "Published"
    published_at.admin_order_field = "post__publish_date"

    def views_30d(self, obj):
        val = getattr(obj, "v_30d", 0)
        return f"{val:,}" if val else "-"
    views_30d.short_description = "🗓️ Views (30d)"
    views_30d.admin_order_field = "v_30d"

    def views_7d(self, obj):
        val = getattr(obj, "v_7d", 0)
        return f"{val:,}" if val else "-"
    views_7d.short_description = "📈 Views (7d)"
    views_7d.admin_order_field = "v_7d"

    def views_24h(self, obj):
        val = getattr(obj, "v_24h", 0)
        return f"{val:,}" if val else "-"
    views_24h.short_description = "📅 Views (24h)"
    views_24h.admin_order_field = "v_24h"

    def views_6h(self, obj):
        val = getattr(obj, "v_6h", 0)
        return f"{val:,}" if val else "-"
    views_6h.short_description = "⚡ Views (6h)"
    views_6h.admin_order_field = "v_6h"

    def formatted_views(self, obj):
        return f"👁️ {obj.total_views:,}"
    formatted_views.short_description = "All Views"
    formatted_views.admin_order_field = "total_views"

    @admin.action(description="🚀 Run Incremental Sync via Celery")
    def trigger_sync_action(self, request, queryset):
        try:
            task = sync_analytics_task.delay()
            self.message_user(
                request,
                f"🚀 Celery background sync task dispatched! (Task ID: {task.id})",
                level=messages.SUCCESS,
            )
        except Exception as exc:
            res = sync_tracking_analytics()
            self.message_user(
                request,
                f"⚠️ Celery dispatch failed ({exc}); ran direct sync: "
                f"Processed {res['processed_events']:,} events in {res['duration_seconds']}s.",
                level=messages.WARNING,
            )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-now/', self.admin_site.admin_view(self.sync_now_view), name='tracking_bloganalytics_sync'),
        ]
        return custom_urls + urls

    def sync_now_view(self, request):
        try:
            task = sync_analytics_task.delay()
            messages.success(
                request,
                f"🚀 Celery background sync task dispatched! (Task ID: {task.id}). "
                f"Unprocessed events are syncing in the background."
            )
        except Exception as exc:
            res = sync_tracking_analytics()
            messages.warning(
                request,
                f"⚠️ Celery dispatch failed ({exc}); ran direct sync: "
                f"Processed {res['processed_events']:,} events in {res['duration_seconds']}s."
            )
        return redirect('admin:tracking_bloganalytics_changelist')


@admin.register(ResourceAnalytics)
class ResourceAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = "admin/tracking/resourceanalytics/change_list.html"
    list_display = (
        'resource_name',
        'resource_type',
        'views_30d',
        'views_7d',
        'views_24h',
        'views_6h',
        'formatted_views',
        'downloads_30d',
        'downloads_7d',
        'downloads_24h',
        'downloads_6h',
        'formatted_downloads',
        'formatted_engagement',
        'last_processed_at',
    )
    list_filter = ('resource_type', 'last_processed_at')
    search_fields = ('resource__name', 'resource_slug')
    readonly_fields = ('resource', 'resource_slug', 'resource_type', 'total_views', 'total_downloads', 'total_engagement', 'unique_visitors', 'last_processed_at', 'created_at')
    actions = ['trigger_sync_action']

    def get_queryset(self, request):
        now = timezone.now()

        # 1. Resource Page Views (30d, 7d, 24h, 6h in a single query)
        res_counts = Event.objects.filter(
            url__icontains="/resources/",
            timestamp__gte=now - timedelta(days=30),
        ).values("url").annotate(
            c_30d=Count("id"),
            c_7d=Count("id", filter=Q(timestamp__gte=now - timedelta(days=7))),
            c_24h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=24))),
            c_6h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=6))),
        )
        res_6h, res_24h, res_7d, res_30d = {}, {}, {}, {}
        for item in res_counts:
            parts = urlparse(item["url"] or "").path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "resources":
                s = parts[1].split("?")[0].strip()
                if s:
                    res_6h[s] = res_6h.get(s, 0) + item["c_6h"]
                    res_24h[s] = res_24h.get(s, 0) + item["c_24h"]
                    res_7d[s] = res_7d.get(s, 0) + item["c_7d"]
                    res_30d[s] = res_30d.get(s, 0) + item["c_30d"]

        # 2. Resource File Downloads (30d, 7d, 24h, 6h in a single query)
        dl_counts = Event.objects.filter(
            event_type="download",
            timestamp__gte=now - timedelta(days=30),
        ).exclude(target_resource__isnull=True).exclude(target_resource="").values("target_resource").annotate(
            c_30d=Count("id"),
            c_7d=Count("id", filter=Q(timestamp__gte=now - timedelta(days=7))),
            c_24h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=24))),
            c_6h=Count("id", filter=Q(timestamp__gte=now - timedelta(hours=6))),
        )
        dl_6h, dl_24h, dl_7d, dl_30d = {}, {}, {}, {}
        for item in dl_counts:
            t = (item.get("target_resource") or "").split("?")[0].strip("/").split("/")[-1].strip()
            if t:
                dl_6h[t] = dl_6h.get(t, 0) + item["c_6h"]
                dl_24h[t] = dl_24h.get(t, 0) + item["c_24h"]
                dl_7d[t] = dl_7d.get(t, 0) + item["c_7d"]
                dl_30d[t] = dl_30d.get(t, 0) + item["c_30d"]

        request._res_totals = {
            "views_6h": sum(res_6h.values()),
            "views_24h": sum(res_24h.values()),
            "views_7d": sum(res_7d.values()),
            "views_30d": sum(res_30d.values()),
            "downloads_6h": sum(dl_6h.values()),
            "downloads_24h": sum(dl_24h.values()),
            "downloads_7d": sum(dl_7d.values()),
            "downloads_30d": sum(dl_30d.values()),
        }

        w_res_30d = [When(resource_slug=s, then=Value(c)) for s, c in res_30d.items()]
        w_res_7d = [When(resource_slug=s, then=Value(c)) for s, c in res_7d.items()]
        w_res_24h = [When(resource_slug=s, then=Value(c)) for s, c in res_24h.items()]
        w_res_6h = [When(resource_slug=s, then=Value(c)) for s, c in res_6h.items()]

        w_dl_30d = [When(resource_slug=s, then=Value(c)) for s, c in dl_30d.items()]
        w_dl_7d = [When(resource_slug=s, then=Value(c)) for s, c in dl_7d.items()]
        w_dl_24h = [When(resource_slug=s, then=Value(c)) for s, c in dl_24h.items()]
        w_dl_6h = [When(resource_slug=s, then=Value(c)) for s, c in dl_6h.items()]

        return self.model._default_manager.get_queryset().select_related("resource").annotate(
            v_30d=Case(*w_res_30d, default=Value(0), output_field=IntegerField()) if w_res_30d else Value(0),
            v_7d=Case(*w_res_7d, default=Value(0), output_field=IntegerField()) if w_res_7d else Value(0),
            v_24h=Case(*w_res_24h, default=Value(0), output_field=IntegerField()) if w_res_24h else Value(0),
            v_6h=Case(*w_res_6h, default=Value(0), output_field=IntegerField()) if w_res_6h else Value(0),
            dl_30d=Case(*w_dl_30d, default=Value(0), output_field=IntegerField()) if w_dl_30d else Value(0),
            dl_7d=Case(*w_dl_7d, default=Value(0), output_field=IntegerField()) if w_dl_7d else Value(0),
            dl_24h=Case(*w_dl_24h, default=Value(0), output_field=IntegerField()) if w_dl_24h else Value(0),
            dl_6h=Case(*w_dl_6h, default=Value(0), output_field=IntegerField()) if w_dl_6h else Value(0),
        )

    def get_ordering(self, request):
        if request.GET.get('o'):
            return super().get_ordering(request)
        return ['-v_30d', '-total_engagement']

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        if hasattr(response, "context_data") and response.context_data:
            totals = getattr(request, "_res_totals", {})
            response.context_data["live_stats"] = {
                "views_6h": f"{totals.get('views_6h', 0):,}",
                "views_24h": f"{totals.get('views_24h', 0):,}",
                "views_7d": f"{totals.get('views_7d', 0):,}",
                "views_30d": f"{totals.get('views_30d', 0):,}",
                "downloads_6h": f"{totals.get('downloads_6h', 0):,}",
                "downloads_24h": f"{totals.get('downloads_24h', 0):,}",
                "downloads_7d": f"{totals.get('downloads_7d', 0):,}",
                "downloads_30d": f"{totals.get('downloads_30d', 0):,}",
            }
        return response

    def resource_name(self, obj):
        return obj.resource.name if obj.resource else obj.resource_slug
    resource_name.short_description = "Resource"

    def views_30d(self, obj):
        val = getattr(obj, "v_30d", 0)
        return f"{val:,}" if val else "-"
    views_30d.short_description = "🗓️ Views (30d)"
    views_30d.admin_order_field = "v_30d"

    def views_7d(self, obj):
        val = getattr(obj, "v_7d", 0)
        return f"{val:,}" if val else "-"
    views_7d.short_description = "📈 Views (7d)"
    views_7d.admin_order_field = "v_7d"

    def views_24h(self, obj):
        val = getattr(obj, "v_24h", 0)
        return f"{val:,}" if val else "-"
    views_24h.short_description = "📅 Views (24h)"
    views_24h.admin_order_field = "v_24h"

    def views_6h(self, obj):
        val = getattr(obj, "v_6h", 0)
        return f"{val:,}" if val else "-"
    views_6h.short_description = "⚡ Views (6h)"
    views_6h.admin_order_field = "v_6h"

    def formatted_views(self, obj):
        return f"👁️ {obj.total_views:,}"
    formatted_views.short_description = "All Views"
    formatted_views.admin_order_field = "total_views"

    def downloads_30d(self, obj):
        val = getattr(obj, "dl_30d", 0)
        return f"{val:,}" if val else "-"
    downloads_30d.short_description = "🗓️ DL (30d)"
    downloads_30d.admin_order_field = "dl_30d"

    def downloads_7d(self, obj):
        val = getattr(obj, "dl_7d", 0)
        return f"{val:,}" if val else "-"
    downloads_7d.short_description = "📈 DL (7d)"
    downloads_7d.admin_order_field = "dl_7d"

    def downloads_24h(self, obj):
        val = getattr(obj, "dl_24h", 0)
        return f"{val:,}" if val else "-"
    downloads_24h.short_description = "📅 DL (24h)"
    downloads_24h.admin_order_field = "dl_24h"

    def downloads_6h(self, obj):
        val = getattr(obj, "dl_6h", 0)
        return f"{val:,}" if val else "-"
    downloads_6h.short_description = "⚡ DL (6h)"
    downloads_6h.admin_order_field = "dl_6h"

    def formatted_downloads(self, obj):
        return f"📥 {obj.total_downloads:,}"
    formatted_downloads.short_description = "All DL"
    formatted_downloads.admin_order_field = "total_downloads"

    def formatted_engagement(self, obj):
        return f"🔥 {obj.total_engagement:,}"
    formatted_engagement.short_description = "Engagement"
    formatted_engagement.admin_order_field = "total_engagement"

    @admin.action(description="🚀 Run Incremental Sync via Celery")
    def trigger_sync_action(self, request, queryset):
        try:
            task = sync_analytics_task.delay()
            self.message_user(
                request,
                f"🚀 Celery background sync task dispatched! (Task ID: {task.id})",
                level=messages.SUCCESS,
            )
        except Exception as exc:
            res = sync_tracking_analytics()
            self.message_user(
                request,
                f"⚠️ Celery dispatch failed ({exc}); ran direct sync: "
                f"Processed {res['processed_events']:,} events in {res['duration_seconds']}s.",
                level=messages.WARNING,
            )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-now/', self.admin_site.admin_view(self.sync_now_view), name='tracking_resourceanalytics_sync'),
        ]
        return custom_urls + urls

    def sync_now_view(self, request):
        try:
            task = sync_analytics_task.delay()
            messages.success(
                request,
                f"🚀 Celery background sync task dispatched! (Task ID: {task.id}). "
                f"Unprocessed events are syncing in the background."
            )
        except Exception as exc:
            res = sync_tracking_analytics()
            messages.warning(
                request,
                f"⚠️ Celery dispatch failed ({exc}); ran direct sync: "
                f"Processed {res['processed_events']:,} events in {res['duration_seconds']}s."
            )
        return redirect('admin:tracking_resourceanalytics_changelist')


