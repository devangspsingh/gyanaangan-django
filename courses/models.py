from django.db import models
from django.utils.text import slugify
from django.db.models import Max
from django.utils import timezone
from datetime import datetime, timedelta
from multiselectfield import MultiSelectField
import io
import cairosvg
from django.template.loader import render_to_string
from gyanaangan.settings import PrivateMediaStorage, PublicMediaStorage


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
    og_image = models.FileField(storage=PublicMediaStorage(), upload_to="og-image/", blank=True, null=True)

    class Meta:
        abstract = True

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
                bytestring=self.generate_og_image_svg().encode(), write_to=png_filelike, unsafe=True
            )
            png_filelike.seek(0)
            
            # Versioned filename
            version = int(datetime.timestamp(datetime.now()))
            filename = f"{self.slug}_v{version}.png"
            
            self.og_image.save(filename, png_filelike, save=False)

class Year(BaseModel):
    year = models.IntegerField()
    slug = models.SlugField(unique=True, blank=True)
    name = models.CharField(max_length=10, blank=True, null=True)
    published = PublishedManager()
    objects = models.Manager()  # Default manager

    drafts = DraftManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.year}-year")
        super(Year, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.year)


class Course(SEOModel):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20, blank=True, null=True)
    common_name = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    years = models.ManyToManyField(Year, related_name="courses")

    published = PublishedManager()
    objects = models.Manager()  # Default manager

    drafts = DraftManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Course, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Stream(SEOModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    abbreviation = models.CharField(max_length=20, blank=True, null=True)
    common_name = models.CharField(max_length=100, blank=True, null=True)
    courses = models.ManyToManyField(Course, related_name="streams")
    years = models.ManyToManyField(Year, related_name="streams")

    published = PublishedManager()
    objects = models.Manager()  # Default manager

    drafts = DraftManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Stream, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Subject(SEOModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    abbreviation = models.CharField(max_length=20, blank=True, null=True)
    common_name = models.CharField(max_length=100, blank=True, null=True)
    stream = models.ManyToManyField(Stream, related_name="subjects", blank=True)
    years = models.ManyToManyField(Year, related_name="subjects")
    last_resource_updated_at = models.DateTimeField(
        null=True, blank=True
    )  # Add this field

    published = PublishedManager()
    objects = models.Manager()  # Default manager

    drafts = DraftManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Subject, self).save(*args, **kwargs)
        self.update_last_resource_updated()
        super(Subject, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_all_available_resource_types(self):
        return self.resources.values_list("resource_type", flat=True).distinct()

    def update_last_resource_updated(self):
        last_updated = self.resources.aggregate(Max("updated_at"))["updated_at__max"]
        if last_updated:
            self.last_resource_updated_at = last_updated

    def get_last_updated_resource(self):
        last_updated = self.last_resource_updated_at
        if last_updated:
            last_updated = last_updated.astimezone()
            now = timezone.now().astimezone()
            diff = now - last_updated

            if diff < timedelta(hours=1):
                return {"status": "updated recently", "exact_time": last_updated}
            elif diff < timedelta(days=1):
                return {"status": "updated today", "exact_time": last_updated}
            elif diff < timedelta(days=7):
                return {"status": "updated this week", "exact_time": last_updated}
            elif diff < timedelta(days=30):
                return {"status": "updated this month", "exact_time": last_updated}
            elif diff < timedelta(days=365):
                return {"status": "updated this year", "exact_time": last_updated}
            else:
                return {
                    "status": f"updated on {last_updated.strftime('%b %Y')}",
                    "exact_time": last_updated,
                }
        return None


class EducationalYear(BaseModel):
    name = models.CharField(max_length=9, unique=True)  # Format: "2023-2024"

    def __str__(self):
        return self.name


class Resource(SEOModel):
    NOTES = "notes"
    PYQ = "pyq"
    LAB_MANUAL = "lab manual"
    VIDEO = "video"
    IMAGE = "image"
    PDF = "pdf"
    RESOURCE_TYPE_CHOICES = [
        (NOTES, "Notes"),
        (PYQ, "Previous Year Question"),
        (LAB_MANUAL, "Lab Manual"),
        (VIDEO, "Video"),
        (IMAGE, "Image"),
        (PDF, "PDF"),
    ]
    RESOURCE_PRIVACY_CHOICES = (
        ("download", "Download"),
        ("view", "View"),
    )

    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, blank=True)
    resource_type = models.CharField(
        max_length=20, choices=RESOURCE_TYPE_CHOICES, db_index=True
    )
    file = models.FileField(storage=PrivateMediaStorage, upload_to="resources/")

    privacy = MultiSelectField(choices=RESOURCE_PRIVACY_CHOICES, default=["view"])

    embed_link = models.URLField(blank=True, null=True)  # For YouTube videos
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resources",
    )
    educational_year = models.ForeignKey(
        EducationalYear, on_delete=models.SET_NULL, null=True, blank=True
    )

    published = PublishedManager()
    objects = models.Manager()  # Default manager

    drafts = DraftManager()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Resource, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.resource_type}"

    @property
    def type(self):
        return self.resource_type

    def get_last_updated_at(self):
        if self.updated_at:
            last_updated = self.updated_at.astimezone()
            now = timezone.now().astimezone()
            diff = now - last_updated
            if diff < timedelta(hours=1):
                return {"status": "updated recently", "exact_time": last_updated}
            elif diff < timedelta(days=1):
                return {"status": "updated today", "exact_time": last_updated}
            elif diff < timedelta(days=7):
                return {"status": "updated this week", "exact_time": last_updated}
            elif diff < timedelta(days=30):
                return {"status": "updated this month", "exact_time": last_updated}
            elif diff < timedelta(days=365):
                return {"status": "updated this year", "exact_time": last_updated}
            else:
                return {
                    "status": f"updated on {last_updated.strftime('%b %Y')}",
                    "exact_time": last_updated,
                }
        return None


class Advertisement(SEOModel):
    title = models.CharField(max_length=100)
    content = models.TextField()
    url = models.URLField()

    def __str__(self):
        return self.title


class Notification(BaseModel):
    IMPORTANCE_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]
    TAG_CHOICES = [
        ("important", "Important"),
        ("new", "New"),
        ("update", "Update"),
        ("info", "Information"),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    importance = models.CharField(
        max_length=10, choices=IMPORTANCE_CHOICES, default="medium"
    )
    tags = models.CharField(max_length=10, choices=TAG_CHOICES, blank=True, null=True)
    show_until = models.DateTimeField(blank=True, null=True)

    published = PublishedManager()
    objects = models.Manager()  # Default manager
    drafts = DraftManager()

    def __str__(self):
        return self.title

    def is_active(self):
        if self.show_until:
            return timezone.now() < self.show_until
        return True


class SpecialPage(SEOModel):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="special_page"
    )
    stream = models.ForeignKey(
        Stream, on_delete=models.CASCADE, related_name="special_page"
    )
    year = models.ForeignKey(
        Year, on_delete=models.CASCADE, related_name="special_page"
    )
    notifications = models.ManyToManyField(
        Notification, related_name="special_pages", blank=True
    )

    published = PublishedManager()
    objects = models.Manager()  # Default manager
    drafts = DraftManager()

    def save(self, *args, **kwargs):
        super(SpecialPage, self).save(*args, **kwargs)

    def __str__(self):
        return (
            f"Special Page for {self.course.name}, {self.stream.name}, {self.year.year}"
        )

    def get_last_updated_subject(self):
        related_subjects = Subject.objects.filter(
            courses=self.course, streams=self.stream, years=self.year
        ).order_by("-updated_at")
        if related_subjects.exists():
            last_subject = related_subjects.first()
            return last_subject.get_last_updated_resource()
        return None
