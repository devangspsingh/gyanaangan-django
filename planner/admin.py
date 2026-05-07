from django.contrib import admin
from .models import StudyPlan, StudyTask, UserTopicKnowledge


class StudyTaskInline(admin.TabularInline):
    model = StudyTask
    extra = 0
    autocomplete_fields = ("topic",)


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exam_date", "hours_per_day", "start_date", "is_active", "created_at")
    list_filter = ("is_active", "exam_date", "start_date")
    search_fields = ("user__username", "user__email", "subjects__name")
    filter_horizontal = ("subjects",)
    inlines = [StudyTaskInline]


@admin.register(StudyTask)
class StudyTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "plan", "topic", "date", "duration", "priority_score", "status")
    list_filter = ("status", "date", "topic__subject")
    search_fields = ("topic__name", "plan__user__username", "plan__user__email")
    autocomplete_fields = ("plan", "topic")


@admin.register(UserTopicKnowledge)
class UserTopicKnowledgeAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "knowledge_level", "updated_at")
    list_filter = ("knowledge_level", "topic__subject")
    search_fields = ("user__username", "user__email", "topic__name")
    autocomplete_fields = ("user", "topic")
