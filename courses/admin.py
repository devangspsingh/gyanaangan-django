from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.core.files.base import ContentFile
import os
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
from .pdf_watermark import add_watermark_to_resources


def generate_og_images(modeladmin, request, queryset):
    for obj in queryset:
        obj.write_og_image()
        obj.save(update_fields=["og_image"])
    modeladmin.message_user(request, "OG images have been generated successfully.")


def add_pdf_watermark(modeladmin, request, queryset):
    """Add GyanAangan branding watermark to PDF resources"""
    from django.contrib import messages
    
    stats = add_watermark_to_resources(queryset, request)
    
    # Prepare detailed message
    message_parts = []
    
    if stats['processed'] > 0:
        message_parts.append(f"✅ Successfully watermarked {stats['processed']} PDF(s)")
    
    if stats['backed_up'] > 0:
        message_parts.append(f"💾 Backed up {stats['backed_up']} original file(s)")
    
    if stats['no_file'] > 0:
        message_parts.append(f"⚠️ Skipped {stats['no_file']} resource(s) with no file")
    
    if stats['not_pdf'] > 0:
        message_parts.append(f"⚠️ Skipped {stats['not_pdf']} non-PDF file(s)")
    
    if stats['failed'] > 0:
        message_parts.append(f"❌ Failed to watermark {stats['failed']} file(s)")
    
    message = " | ".join(message_parts) if message_parts else "No resources were processed"
    
    # Determine message level
    if stats['processed'] > 0 and stats['failed'] == 0:
        level = messages.SUCCESS
    elif stats['failed'] > 0:
        level = messages.WARNING
    else:
        level = messages.INFO
    
    modeladmin.message_user(request, message, level=level)


def restore_original_files(modeladmin, request, queryset):
    """Restore original files from backup (remove watermark)"""
    from django.contrib import messages
    
    restored = 0
    no_backup = 0
    failed = 0
    
    for resource in queryset:
        if not resource.original_file:
            no_backup += 1
            continue
        
        try:
            # Get original file content
            resource.original_file.seek(0)
            original_content = resource.original_file.read()
            
            # Get original filename
            original_filename = os.path.basename(resource.original_file.name)
            
            # Delete current watermarked file
            if resource.file:
                resource.file.delete(save=False)
            
            # Restore original file to main file field
            resource.file.save(
                original_filename,
                ContentFile(original_content),
                save=False
            )
            
            # Delete the backup (optional - keep it commented if you want to keep backups)
            # resource.original_file.delete(save=False)
            
            resource.save()
            restored += 1
            print(f"✅ Restored original file for: {resource.name}")
            
        except Exception as e:
            failed += 1
            print(f"❌ Failed to restore {resource.name}: {str(e)}")
    
    # Prepare message
    message_parts = []
    if restored > 0:
        message_parts.append(f"✅ Restored {restored} original file(s)")
    if no_backup > 0:
        message_parts.append(f"⚠️ {no_backup} resource(s) have no backup")
    if failed > 0:
        message_parts.append(f"❌ Failed to restore {failed} file(s)")
    
    message = " | ".join(message_parts) if message_parts else "No resources processed"
    level = messages.SUCCESS if restored > 0 and failed == 0 else messages.WARNING
    
    modeladmin.message_user(request, message, level=level)


add_pdf_watermark.short_description = _("Add GyanAangan watermark to PDF files")
restore_original_files.short_description = _("Restore original files (remove watermark)")


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
    list_display = ["name", "resource_type", "slug", "status", "has_backup", "educational_year", "created_at", "updated_at"]
    list_filter = ["status", "resource_type", "subject", "educational_year", "created_at", "updated_at"]
    search_fields = ["name", "resource_type", "slug"]
    ordering = ["-created_at", "-updated_at"]
    actions = [
        make_published,
        make_draft,
        add_pdf_watermark,  # Add watermark action
        restore_original_files,  # Restore original action
    ]
    
    def has_backup(self, obj):
        """Show if resource has original file backup"""
        return bool(obj.original_file)
    has_backup.boolean = True
    has_backup.short_description = "Has Backup"
    
    fieldsets = (
        (None, {"fields": ("name", "slug", "resource_type", "status")}),
        (
            "Resource Content",
            {
                "fields": ("file", "original_file", "resource_link", "embed_link", "content"),
                "description": "Provide at least one: File upload, Resource link (Google Drive/Dropbox), Embed link (YouTube only), or Rich text content. Original file is automatically backed up when watermarking.",
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
