from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
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
    list_display = ('post_title', 'post_slug', 'formatted_views', 'last_processed_at')
    search_fields = ('post__title', 'post_slug')
    readonly_fields = ('post', 'post_slug', 'total_views', 'unique_visitors', 'last_processed_at', 'created_at')
    ordering = ('-total_views',)
    actions = ['trigger_sync_action']

    def post_title(self, obj):
        return obj.post.title if obj.post else obj.post_slug
    post_title.short_description = "Blog Post"

    def formatted_views(self, obj):
        return f"👁️ {obj.total_views:,}"
    formatted_views.short_description = "Total Views"
    formatted_views.admin_order_field = "total_views"

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
    list_display = ('resource_name', 'resource_type', 'formatted_views', 'formatted_downloads', 'formatted_engagement', 'last_processed_at')
    list_filter = ('resource_type', 'last_processed_at')
    search_fields = ('resource__name', 'resource_slug')
    readonly_fields = ('resource', 'resource_slug', 'resource_type', 'total_views', 'total_downloads', 'total_engagement', 'unique_visitors', 'last_processed_at', 'created_at')
    ordering = ('-total_engagement', '-total_views')
    actions = ['trigger_sync_action']

    def resource_name(self, obj):
        return obj.resource.name if obj.resource else obj.resource_slug
    resource_name.short_description = "Resource"

    def formatted_views(self, obj):
        return f"👁️ {obj.total_views:,}"
    formatted_views.short_description = "Views"
    formatted_views.admin_order_field = "total_views"

    def formatted_downloads(self, obj):
        return f"📥 {obj.total_downloads:,}"
    formatted_downloads.short_description = "Downloads"
    formatted_downloads.admin_order_field = "total_downloads"

    def formatted_engagement(self, obj):
        return f"⚡ {obj.total_engagement:,}"
    formatted_engagement.short_description = "Total Engagement"
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

