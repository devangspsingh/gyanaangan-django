from django.contrib import admin
from django.utils.html import format_html
from .models import Event, EventRegistration, ManualParticipant


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0
    fields = ['user', 'registration_number', 'status', 'attendance_status']
    readonly_fields = ['registration_number']
    can_delete = False


class ManualParticipantInline(admin.TabularInline):
    model = ManualParticipant
    extra = 0
    fields = ['name', 'email', 'phone', 'attendance_status']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'organization', 'event_type', 'start_datetime',
        'status', 'is_published', 'is_featured', 'registered_count',
        'view_count'
    ]
    list_filter = [
        'event_type', 'status', 'is_published', 'is_featured',
        'is_online', 'start_datetime', 'created_at'
    ]
    search_fields = [
        'title', 'description', 'organization__name',
        'venue_name', 'tags'
    ]
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = [
        'created_at', 'updated_at', 'view_count',
        'registered_count', 'present_count', 'is_past',
        'is_ongoing', 'is_upcoming', 'spots_remaining'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'organization', 'title', 'slug', 'description',
                'short_description', 'event_type', 'event_image'
            )
        }),
        ('Event Timing', {
            'fields': (
                'start_datetime', 'end_datetime', 'registration_deadline'
            )
        }),
        ('Location', {
            'fields': (
                'is_online', 'venue_name', 'venue_address',
                'google_maps_link', 'meeting_link'
            )
        }),
        ('Registration', {
            'fields': (
                'max_participants', 'registration_fee',
                'is_registration_open'
            )
        }),
        ('Event Details', {
            'fields': (
                'prizes', 'rules', 'eligibility_criteria',
                'schedule', 'tags'
            ),
            'classes': ('collapse',)
        }),
        ('Contact Information', {
            'fields': (
                'contact_person', 'contact_email', 'contact_phone'
            )
        }),
        ('Status & Publishing', {
            'fields': (
                'status', 'is_published', 'is_featured', 'created_by'
            )
        }),
        ('Statistics', {
            'fields': (
                'view_count', 'registered_count', 'present_count',
                'is_past', 'is_ongoing', 'is_upcoming', 'spots_remaining'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [EventRegistrationInline, ManualParticipantInline]
    
    actions = [
        'publish_events', 'unpublish_events', 'mark_as_featured',
        'mark_as_unfeatured', 'close_registration', 'open_registration'
    ]
    
    def publish_events(self, request, queryset):
        updated = queryset.update(is_published=True, status='PUBLISHED')
        self.message_user(request, f'{updated} events published.')
    publish_events.short_description = 'Publish selected events'
    
    def unpublish_events(self, request, queryset):
        updated = queryset.update(is_published=False, status='DRAFT')
        self.message_user(request, f'{updated} events unpublished.')
    unpublish_events.short_description = 'Unpublish selected events'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} events marked as featured.')
    mark_as_featured.short_description = 'Mark selected events as featured'
    
    def mark_as_unfeatured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} events marked as unfeatured.')
    mark_as_unfeatured.short_description = 'Remove featured status from selected events'
    
    def close_registration(self, request, queryset):
        updated = queryset.update(is_registration_open=False)
        self.message_user(request, f'Registration closed for {updated} events.')
    close_registration.short_description = 'Close registration for selected events'
    
    def open_registration(self, request, queryset):
        updated = queryset.update(is_registration_open=True)
        self.message_user(request, f'Registration opened for {updated} events.')
    open_registration.short_description = 'Open registration for selected events'


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'registration_number', 'user', 'event', 'status',
        'attendance_status', 'created_at'
    ]
    list_filter = [
        'status', 'attendance_status', 'event__event_type',
        'created_at'
    ]
    search_fields = [
        'registration_number', 'user__username', 'user__email',
        'event__title'
    ]
    readonly_fields = [
        'registration_number', 'created_at', 'updated_at',
        'marked_present_by', 'marked_present_at'
    ]
    
    fieldsets = (
        ('Registration Information', {
            'fields': (
                'event', 'user', 'registration_number', 'status'
            )
        }),
        ('Attendance', {
            'fields': (
                'attendance_status', 'marked_present_by', 'marked_present_at'
            )
        }),
        ('Additional Information', {
            'fields': ('additional_info',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_present', 'mark_as_absent', 'confirm_registrations',
        'cancel_registrations'
    ]
    
    def mark_as_present(self, request, queryset):
        for registration in queryset:
            registration.mark_present(request.user)
        self.message_user(request, f'{queryset.count()} registrations marked as present.')
    mark_as_present.short_description = 'Mark selected registrations as present'
    
    def mark_as_absent(self, request, queryset):
        for registration in queryset:
            registration.mark_absent()
        self.message_user(request, f'{queryset.count()} registrations marked as absent.')
    mark_as_absent.short_description = 'Mark selected registrations as absent'
    
    def confirm_registrations(self, request, queryset):
        updated = queryset.update(status='CONFIRMED')
        self.message_user(request, f'{updated} registrations confirmed.')
    confirm_registrations.short_description = 'Confirm selected registrations'
    
    def cancel_registrations(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'{updated} registrations cancelled.')
    cancel_registrations.short_description = 'Cancel selected registrations'


@admin.register(ManualParticipant)
class ManualParticipantAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'event', 'organization_name',
        'attendance_status', 'added_by', 'created_at'
    ]
    list_filter = ['attendance_status', 'event__event_type', 'created_at']
    search_fields = [
        'name', 'email', 'phone', 'organization_name',
        'event__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'added_by']
    
    fieldsets = (
        ('Participant Information', {
            'fields': (
                'event', 'name', 'email', 'phone',
                'organization_name', 'designation'
            )
        }),
        ('Attendance', {
            'fields': ('attendance_status',)
        }),
        ('Metadata', {
            'fields': ('added_by', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_present', 'mark_as_absent']
    
    def mark_as_present(self, request, queryset):
        updated = queryset.update(attendance_status='PRESENT')
        self.message_user(request, f'{updated} participants marked as present.')
    mark_as_present.short_description = 'Mark selected participants as present'
    
    def mark_as_absent(self, request, queryset):
        updated = queryset.update(attendance_status='ABSENT')
        self.message_user(request, f'{updated} participants marked as absent.')
    mark_as_absent.short_description = 'Mark selected participants as absent'
