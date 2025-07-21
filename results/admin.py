from django.contrib import admin
from .models import ResultQuery, StudentResult, ManualResultEntry


@admin.register(ResultQuery)
class ResultQueryAdmin(admin.ModelAdmin):
    list_display = ['roll_number', 'user', 'ip_address', 'timestamp', 'result_found', 'semester', 'branch']
    list_filter = ['result_found', 'semester', 'branch', 'timestamp']
    search_fields = ['roll_number', 'user__username', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


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
