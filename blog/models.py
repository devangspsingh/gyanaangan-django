import io
import cairosvg
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField
from gyanaangan.settings import PublicMediaStorage
from taggit.managers import TaggableManager
from datetime import datetime, timedelta
from django.utils import timezone
from django.template.loader import render_to_string


class BaseModel(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")

    class Meta:
        abstract = True
        ordering = ["-updated_at"]


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status="published")


class DraftManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status="draft")


class SEOModel(BaseModel):
    description = models.TextField(blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    keywords = models.CharField(max_length=200, blank=True)
    og_image = models.FileField(
        storage=PublicMediaStorage(), upload_to="og-image/", blank=True, null=True
    )

    class Meta:
        abstract = True
        ordering = ["-updated_at"]

    def generate_og_image_svg(self) -> str:
        """Generate the SVG for the Open Graph image as a string"""
        template_name = f"og-image.html"
        return render_to_string(template_name, {"item": self.name})

    def delete_previous_og_image(self):
        """Delete the previous Open Graph image if it exists"""
        if self.og_image:
            self.og_image.delete(save=False)

    def write_og_image(self) -> None:
        """Write the Open Graph image to the storage as a PNG with versioning"""
        if self.status == "published":
            # Delete previous image
            self.delete_previous_og_image()

            # Generate new image
            png_filelike = io.BytesIO()
            cairosvg.svg2png(
                bytestring=self.generate_og_image_svg().encode(),
                write_to=png_filelike,
                unsafe=True,
            )
            png_filelike.seek(0)

            # Versioned filename
            version = int(datetime.timestamp(datetime.now()))
            filename = f"{self.slug}_v{version}.png"

            self.og_image.save(filename, png_filelike, save=False)


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class BlogPost(SEOModel):
    title = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blog_posts"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="posts"
    )
    content = RichTextUploadingField()  # Supports rich text and media uploads
    excerpt = models.TextField(
        max_length=500, help_text="Short summary of the post", blank=True
    )
    featured_image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    tags = TaggableManager()  # Add tags to posts for better search and SEO
    publish_date = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    sticky_post = models.BooleanField(
        default=False, help_text="Sticky posts stay on top of the homepage."
    )
    view_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(
        default=0, help_text="Estimated reading time in minutes."
    )

    objects = models.Manager()  # Default manager
    published = PublishedManager()  # Custom manager for published posts
    drafts = DraftManager()  # Custom manager for drafts

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        # Auto-calculate reading time based on word count
        words_per_minute = 200
        word_count = len(self.content.split())
        self.reading_time = word_count // words_per_minute

        # If published status and no publish date, set it to now
        if self.status == "published" and not self.publish_date:
            self.publish_date = timezone.now()

        super(BlogPost, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_detail", args=[self.slug])

    class Meta:
        ordering = ["-publish_date", "-created_at"]
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"


class SocialMediaShare(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="shares")
    platform = models.CharField(
        max_length=50,
        choices=[
            ("facebook", "Facebook"),
            ("twitter", "Twitter"),
            ("linkedin", "LinkedIn"),
            ("pinterest", "Pinterest"),
            ("reddit", "Reddit"),
        ],
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shared on {self.platform} for post {self.post.title}"
