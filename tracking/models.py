from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class Visitor(models.Model):
    """
    Represents a unique visitor (browser/device) identified by a persistent ID.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor_id = models.CharField(max_length=255, unique=True, help_text="Unique ID from FingerprintJS or similar")
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True, unpack_ipv4=True)
    device_type = models.CharField(max_length=50, blank=True, null=True) # e.g., mobile, tablet, desktop
    os = models.CharField(max_length=50, blank=True, null=True)
    browser = models.CharField(max_length=50, blank=True, null=True)
    
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Detailed Info
    device_brand = models.CharField(max_length=50, blank=True, null=True)
    device_model = models.CharField(max_length=50, blank=True, null=True)
    os_version = models.CharField(max_length=50, blank=True, null=True)
    screen_resolution = models.CharField(max_length=50, blank=True, null=True)

    ACCESS_STATUS_CHOICES = (
        ('allow', 'Allow'),
        ('force_login', 'Force Login'),
        ('block', 'Block'),
    )
    access_status = models.CharField(max_length=20, choices=ACCESS_STATUS_CHOICES, default='allow')

    def __str__(self):
        return f"Visitor {self.visitor_id[:8]}..."

class UserVisitor(models.Model):
    """
    Links a User to a Visitor (Device).
    Answer: "Which devices does this user use?"
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='known_devices')
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='users')
    last_used_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'visitor')

    def __str__(self):
        return f"{self.user} on {self.visitor}"

class Session(models.Model):
    """
    Represents a single browsing session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='analytics_sessions')
    
    start_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Optional: Store session metadata like referrer, campaign source etc.
    referrer = models.URLField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"Session {self.id} ({self.start_time})"
    
    @property
    def duration(self):
        if self.last_activity and self.start_time:
            return (self.last_activity - self.start_time).total_seconds()
        return 0

class Event(models.Model):
    """
    Represents a discrete action taken by a visitor.
    """
    EVENT_TYPES = (
        ('page_view', 'Page View'),
        ('click', 'Click'),
        ('download', 'Download'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('custom', 'Custom'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='custom')
    
    url = models.URLField(max_length=500, blank=True, null=True, help_text="Page URL where event occurred")
    target_resource = models.CharField(max_length=500, blank=True, null=True, help_text="Target URL or File ID for clicks/downloads")
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Store flexible JSON data for custom attributes
    metadata = models.JSONField(default=dict, blank=True)
    is_processed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flag indicating whether this event has been processed into analytics models",
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['session']),
            models.Index(fields=['is_processed', 'event_type']),
        ]

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"


class BlogAnalytics(models.Model):
    """
    Incremental aggregated analytics for blog posts.
    """
    post = models.OneToOneField(
        'blog.BlogPost',
        on_delete=models.CASCADE,
        related_name='tracking_analytics',
    )
    post_slug = models.CharField(max_length=255, db_index=True)
    total_views = models.PositiveIntegerField(default=0, db_index=True)
    unique_visitors = models.PositiveIntegerField(default=0)
    last_processed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Blog Analytics"
        verbose_name_plural = "Blog Analytics"
        ordering = ['-total_views']

    def __str__(self):
        return f"{self.post_slug}: {self.total_views:,} views"


class ResourceAnalytics(models.Model):
    """
    Incremental aggregated analytics for educational resources.
    """
    resource = models.OneToOneField(
        'courses.Resource',
        on_delete=models.CASCADE,
        related_name='tracking_analytics',
    )
    resource_slug = models.CharField(max_length=255, db_index=True)
    resource_type = models.CharField(max_length=50, blank=True, db_index=True)
    total_views = models.PositiveIntegerField(default=0, db_index=True)
    total_downloads = models.PositiveIntegerField(default=0, db_index=True)
    total_engagement = models.PositiveIntegerField(default=0, db_index=True)
    unique_visitors = models.PositiveIntegerField(default=0)
    last_processed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resource Analytics"
        verbose_name_plural = "Resource Analytics"
        ordering = ['-total_engagement', '-total_views']

    def __str__(self):
        return f"{self.resource_slug}: {self.total_views:,} views, {self.total_downloads:,} dls"
