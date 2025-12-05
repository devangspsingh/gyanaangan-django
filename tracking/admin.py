from django.contrib import admin
from .models import Visitor, Session, Event

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('visitor_id', 'ip_address', 'device_type', 'os', 'browser','first_seen', 'last_seen')
    search_fields = ('visitor_id', 'ip_address', 'user_agent')
    readonly_fields = ('id', 'first_seen', 'last_seen')

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
    list_display = ('event_type', 'url', 'timestamp', 'session_link')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('url', 'target_resource')
    readonly_fields = ('id', 'timestamp')

    def session_link(self, obj):
        return obj.session
