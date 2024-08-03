from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from .models import (
    Course,
    SpecialPage,
    Stream,
    Subject,
    Resource,
    Year,
    EducationalYear,
    Advertisement,
)
from .forms import CourseForm, StreamForm, SubjectForm, ResourceForm
from .forms import ResourceForm
from django.utils.translation import gettext_lazy as _


def make_published(modeladmin, request, queryset):
    queryset.update(status="published")
    modeladmin.message_user(request, _("Selected items have been marked as published."))


def make_draft(modeladmin, request, queryset):
    queryset.update(status="draft")
    modeladmin.message_user(request, _("Selected items have been marked as draft."))


make_published.short_description = _("Mark selected items as published")
make_draft.short_description = _("Mark selected items as draft")


class BaseModelAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "created_at", "updated_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["id"]
    ordering = ["id"]
    date_hierarchy = "created_at"
    actions = [make_published, make_draft]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Year)
class YearAdmin(BaseModelAdmin):
    list_display = ["year", "slug"]
    search_fields = ["year", "slug"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(EducationalYear)
class EducationalYearAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Course)
class CourseAdmin(BaseModelAdmin):
    form = CourseForm
    list_display = ["name", "abbreviation", "common_name", "slug", "status"]
    search_fields = ["name", "abbreviation", "common_name", "slug"]
    list_filter = ["status", "years"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "status", "years")}),
        (
            "Additional Info",
            {
                "classes": ("collapse",),
                "fields": (
                    "abbreviation",
                    "common_name",
                    "description",
                    "meta_description",
                    "keywords",
                    "image",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Stream)
class StreamAdmin(BaseModelAdmin):
    form = StreamForm
    list_display = ["name", "abbreviation", "common_name", "slug", "status"]
    search_fields = ["name", "abbreviation", "common_name", "slug"]
    list_filter = ["status", "courses"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "status", "courses","years")}),
        (
            "Additional Info",
            {
                "classes": ("collapse",),
                "fields": (
                    "abbreviation",
                    "common_name",
                    "description",
                    "meta_description",
                    "keywords",
                    "image",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Subject)
class SubjectAdmin(BaseModelAdmin):
    form = SubjectForm
    list_display = ["name", "abbreviation", "common_name", "slug", "status"]
    search_fields = ["name", "abbreviation", "common_name", "slug"]
    list_filter = ["status", "stream"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "status", "stream","years")}),
        (
            "Additional Info",
            {
                "classes": ("collapse",),
                "fields": (
                    "abbreviation",
                    "common_name",
                    "description",
                    "meta_description",
                    "keywords",
                    "image",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Resource)
class ResourceAdmin(BaseModelAdmin):
    form = ResourceForm
    list_display = ["title", "resource_type", "slug", "status", "educational_year"]
    search_fields = ["title", "resource_type", "slug"]
    list_filter = ["status", "resource_type", "subject", "educational_year"]
    fieldsets = (
        (None, {"fields": ("title", "slug", "resource_type", "status")}),
        (
            "File and Links",
            {"fields": ("file", "privacy", "embed_link", "description")},
        ),
        ("Associations", {"fields": ("subject", "educational_year")}),
        (
            "Additional Info",
            {
                "classes": ("collapse",),
                "fields": ("meta_description", "keywords", "image"),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Advertisement)
class AdvertisementAdmin(BaseModelAdmin):
    list_display = ["title", "content", "url"]
    search_fields = ["title", "content", "url"]
    

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()

from django.contrib import admin
from .models import Notification

class NotificationAdmin(BaseModelAdmin):
    list_display = ('title', 'importance', 'tags', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'importance', 'tags', 'created_at')
    search_fields = ('title', 'message')

# SpecialPageAdmin class
class SpecialPageAdmin(BaseModelAdmin):
    list_display = ["course", "stream", "year", "status", "updated_at"]
    search_fields = ["course__name", "stream__name", "year__year"]
    list_filter = ["status", "course", "stream", "year"]
    fieldsets = (
        (None, {"fields": ("course", "stream", "year", "status")}),
        ("Additional Info", {
            "classes": ("collapse",),
            "fields": ("description", "meta_description", "keywords", "image", "notifications"),
        }),
    )
admin.site.register(Notification, NotificationAdmin)
admin.site.register(SpecialPage, SpecialPageAdmin)