from django.contrib import admin
from .models import BlogPost, Category


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    # List view customization
    list_display = (
        "title",
        "author",
        "status",
        "publish_date",
        "is_featured",
        "view_count",
    )
    list_filter = ("status", "publish_date", "author", "is_featured")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)
    date_hierarchy = "publish_date"
    ordering = ["status", "publish_date"]

    # Fields to show in the admin form
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "slug",
                    "author",
                    "category",
                    "content",
                    "excerpt",
                    "featured_image",
                )
            },
        ),
        (
            "SEO Settings",
            {
                "fields": ("meta_description", "keywords", "og_image"),
            },
        ),
        (
            "Publication Settings",
            {
                "fields": (
                    "status",
                    "publish_date",
                    "is_featured",
                    "sticky_post",
                    "view_count",
                    "reading_time",
                ),
            },
        ),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
