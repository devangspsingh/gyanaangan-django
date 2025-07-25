from django.contrib import admin
from .models import ResultQuery, StudentResult, ManualResultEntry
from django.utils.html import format_html


class UserAnonymousFilter(admin.SimpleListFilter):
    title = 'Anonymous/User'
    parameter_name = 'user_type'

    def lookups(self, request, model_admin):
        return (
            ('anonymous', 'Anonymous'),
            ('user', 'User'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'anonymous':
            return queryset.filter(user__isnull=True)
        if value == 'user':
            return queryset.filter(user__isnull=False)
        return queryset


@admin.register(ResultQuery)
class ResultQueryAdmin(admin.ModelAdmin):
    list_display = [
        'roll_number_with_name', 'user_display', 'ip_address', 'timestamp',
        'result_found', 'semester', 'branch'
    ]
    list_filter = [
        'result_found', 'semester', 'branch', 'timestamp', UserAnonymousFilter
    ]
    search_fields = [
        'roll_number', 'user__username', 'ip_address'
    ]
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

    def roll_number_with_name(self, obj):
        # Try to get the name from related StudentResult or ManualResultEntry
        name = None
        # Try StudentResult
        try:
            name = StudentResult.objects.get(roll_number=obj.roll_number).name
        except StudentResult.DoesNotExist:
            # Try ManualResultEntry
            try:
                name = ManualResultEntry.objects.get(roll_number=obj.roll_number).name
            except ManualResultEntry.DoesNotExist:
                name = None
        if name:
            return f"{obj.roll_number} ({name})"
        return obj.roll_number

    roll_number_with_name.short_description = "Roll Number (Name)"

    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return format_html('<span style="color: #888;">Anonymous</span>')

    user_display.short_description = "User"

    def get_search_results(self, request, queryset, search_term):
        # Optionally, allow searching by student name
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        # Search in StudentResult and ManualResultEntry for matching names
        student_results = StudentResult.objects.filter(name__icontains=search_term)
        manual_results = ManualResultEntry.objects.filter(name__icontains=search_term)
        roll_numbers = list(student_results.values_list('roll_number', flat=True)) + \
                       list(manual_results.values_list('roll_number', flat=True))
        if roll_numbers:
            queryset |= self.model.objects.filter(roll_number__in=roll_numbers)
        return queryset, use_distinct


@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = ['roll_number', 'name', 'father_name', 'total_marks', 'percentage', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['roll_number', 'name', 'father_name']
    readonly_fields = ['total_marks', 'percentage', 'created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ['roll_number']
        return self.readonly_fields


@admin.register(ManualResultEntry)
class ManualResultEntryAdmin(admin.ModelAdmin):
    list_display = ['roll_number', 'name', 'user', 'total_marks', 'percentage', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['roll_number', 'name', 'user__username']
    readonly_fields = ['total_marks', 'percentage', 'created_at', 'updated_at']
