from django.db import models
from django.db.models import Q
from django.utils import timezone
from gyanaangan.settings import PublicMediaStorage

class SEODetail(models.Model):
    page_name = models.CharField(max_length=100, unique=True,blank=True,null=True)
    title = models.CharField(max_length=255)
    meta_description = models.TextField()
    og_image = models.ImageField(storage=PublicMediaStorage,upload_to='og_images/', blank=True, null=True)
    site_name = models.CharField(max_length=255, default='Gyan Aangan')

    def __str__(self):
        return self.title


class PublishedBannerManager(models.Manager):
    def get_queryset(self):
        """Returns only active banners that are within their active period."""
        now = timezone.now()
        return super().get_queryset().filter(
            is_active=True,
            active_from__lte=now
        ).filter(
            Q(active_until__isnull=True) | Q(active_until__gte=now)
        )


class Banner(models.Model):
    """
    Model for managing promotional banners/sliders on the website.
    Supports time-based activation and priority-based ordering.
    """
    title = models.CharField(
        max_length=200,
        help_text="Internal title for the banner (not displayed to users)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description or alt text for the banner"
    )
    image = models.ImageField(
        storage=PublicMediaStorage,
        upload_to='banners/',
        help_text="Banner image (recommended size: 1600x324px with aspect ratio 4.94:1)"
    )
    mobile_image = models.ImageField(
        storage=PublicMediaStorage,
        upload_to='banners/mobile/',
        blank=True,
        null=True,
        help_text="[DEPRECATED] Optional mobile image - Main image is now used for all devices"
    )
    link_url = models.URLField(
        blank=True,
        null=True,
        help_text="Optional URL to redirect when banner is clicked"
    )
    link_text = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional call-to-action text (e.g., 'Learn More', 'Get Started')"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Mark as primary banner (only one should be primary at a time)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle banner visibility"
    )
    active_from = models.DateTimeField(
        default=timezone.now,
        help_text="Banner will be visible from this date/time"
    )
    active_until = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Banner will be hidden after this date/time (leave empty for no expiration)"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Lower numbers appear first (0 = highest priority)"
    )
    click_count = models.IntegerField(
        default=0,
        editable=False,
        help_text="Number of times this banner has been clicked"
    )
    view_count = models.IntegerField(
        default=0,
        editable=False,
        help_text="Number of times this banner has been viewed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()  # Default manager
    active = PublishedBannerManager()  # Custom manager for active banners

    class Meta:
        ordering = ['display_order', '-is_primary', '-created_at']
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'
        indexes = [
            models.Index(fields=['is_active', 'active_from', 'active_until']),
            models.Index(fields=['display_order', 'is_primary']),
        ]

    def __str__(self):
        status = "Active" if self.is_currently_active() else "Inactive"
        primary = " (Primary)" if self.is_primary else ""
        return f"{self.title} - {status}{primary}"

    def is_currently_active(self):
        """Check if banner is currently active based on time range."""
        now = timezone.now()
        if not self.is_active or self.active_from > now:
            return False
        # If active_until is None, banner is active forever
        if self.active_until is None:
            return True
        return self.active_until >= now

    def save(self, *args, **kwargs):
        # If this banner is set as primary, remove primary flag from others
        if self.is_primary:
            Banner.objects.filter(is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def increment_view_count(self):
        """Increment view count atomically."""
        Banner.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)

    def increment_click_count(self):
        """Increment click count atomically."""
        Banner.objects.filter(pk=self.pk).update(click_count=models.F('click_count') + 1)
