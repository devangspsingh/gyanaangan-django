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
    Notification,
)
from .forms import CourseForm, StreamForm, SubjectForm, ResourceForm
from django.utils.translation import gettext_lazy as _


def generate_og_images(modeladmin, request, queryset):
    for obj in queryset:
        obj.write_og_image()
        obj.save(update_fields=["og_image"])
    modeladmin.message_user(request, "OG images have been generated successfully.")


def make_published(modeladmin, request, queryset):
    queryset.update(status="published")
    modeladmin.message_user(request, _("Selected items have been marked as published."))


def make_draft(modeladmin, request, queryset):
    queryset.update(status="draft")
    modeladmin.message_user(request, _("Selected items have been marked as draft."))


make_published.short_description = _("Mark selected items as published")
make_draft.short_description = _("Mark selected items as draft")


class BaseModelAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "status", "created_at", "updated_at"]  # Added created_at and updated_at
    list_filter = ["status", "created_at", "updated_at"]  # Added created_at and updated_at filters
    search_fields = ["id", "name"]
    ordering = ["-created_at"]  # Default sort by newest first
    date_hierarchy = "created_at"
    actions = [
        make_published,
        make_draft,
        generate_og_images,
    ]  # Add the generate_og_images action

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
    list_display = ["name", "abbreviation", "common_name", "slug", "status", "created_at", "updated_at"]
    list_filter = ["status", "years", "created_at", "updated_at"]
    search_fields = ["name", "abbreviation", "common_name", "slug"]
    ordering = ["-created_at", "-updated_at"]
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
                    "og_image",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Stream)
class StreamAdmin(BaseModelAdmin):
    form = StreamForm
    list_display = ["name", "abbreviation", "common_name", "slug", "status", "created_at", "updated_at"]
    list_filter = ["status", "courses", "created_at", "updated_at"]
    search_fields = ["name", "abbreviation", "common_name", "slug"]
    ordering = ["-created_at", "-updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "status", "courses", "years")}),
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
                    "og_image",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Subject)
class SubjectAdmin(BaseModelAdmin):
    form = SubjectForm
    list_display = ["name", "abbreviation", "common_name", "slug", "status", "created_at", "updated_at"]
    list_filter = ["status", "stream", "created_at", "updated_at"]
    search_fields = ["name", "abbreviation", "common_name", "slug"]
    ordering = ["-created_at", "-updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "status", "stream", "years")}),
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
                    "og_image",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Resource)
class ResourceAdmin(BaseModelAdmin):
    form = ResourceForm
    list_display = ["name", "resource_type", "slug", "status", "educational_year", "created_at", "updated_at"]
    list_filter = ["status", "resource_type", "subject", "educational_year", "created_at", "updated_at"]
    search_fields = ["name", "resource_type", "slug"]
    ordering = ["-created_at", "-updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "resource_type", "status")}),
        (
            "Resource Content",
            {
                "fields": ("file", "resource_link", "embed_link", "content"),
                "description": "Provide at least one: File upload, Resource link (Google Drive/Dropbox), Embed link (YouTube only), or Rich text content.",
            },
        ),
        (
            "Settings & Description",
            {"fields": ("privacy", "description")},
        ),
        ("Associations", {"fields": ("subject", "educational_year")}),
        (
            "SEO & Meta",
            {
                "classes": ("collapse",),
                "fields": ("meta_description", "keywords", "og_image"),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ["title", "content", "url"]
    search_fields = ["title", "content", "url"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()

    actions = [
        make_published,
        make_draft,
    ]


class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "importance", "tags", "status", "created_at", "updated_at")
    list_filter = ("status", "importance", "tags", "created_at")
    search_fields = ("title", "message")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return self.model.objects.get_queryset()

    actions = [
        make_published,
        make_draft,
    ]  # Add the generate_og_images action


@admin.register(SpecialPage)
class SpecialPageAdmin(BaseModelAdmin):
    list_display = ["course", "stream", "year", "status", "updated_at"]
    search_fields = ["course__name", "stream__name", "year__year"]
    list_filter = ["status", "course", "stream", "year"]
    fieldsets = (
        (None, {"fields": ("course", "stream", "year", "status")}),
        (
            "Additional Info",
            {
                "classes": ("collapse",),
                "fields": (
                    "description",
                    "meta_description",
                    "keywords",
                    "og_image",
                    "notifications",
                ),
            },
        ),
    )


admin.site.register(Notification, NotificationAdmin)
