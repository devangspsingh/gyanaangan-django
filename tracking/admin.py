from django.contrib import admin
from .models import Visitor, Session, Event, UserVisitor

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('visitor_id', 'ip_address', 'device_type', 'os', 'browser','first_seen', 'last_seen')
    search_fields = ('visitor_id', 'ip_address', 'user_agent')
    readonly_fields = ('id', 'first_seen', 'last_seen', 'device_brand', 'device_model', 'os_version')

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
    list_display = ('event_type', 'url', 'get_user', 'get_ip', 'timestamp')
    list_filter = ('event_type', 'timestamp', 'session__user', 'session__visitor__ip_address')
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
