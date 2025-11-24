import os
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from organization.models import Organization, BaseModel


def event_image_upload_path(instance, filename):
    """Upload path for event images"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"events/{instance.slug}/", filename)


class Event(BaseModel):
    """
    Model for events created by organizations.
    Supports both online and offline events with rich details.
    """
    EVENT_TYPE_CHOICES = [
        ('WORKSHOP', 'Workshop'),
        ('SEMINAR', 'Seminar'),
        ('COMPETITION', 'Competition'),
        ('HACKATHON', 'Hackathon'),
        ('WEBINAR', 'Webinar'),
        ('CONFERENCE', 'Conference'),
        ('MEETUP', 'Meetup'),
        ('CULTURAL', 'Cultural Event'),
        ('SPORTS', 'Sports Event'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Basic Information
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='events',
        help_text="Organization hosting this event"
    )
    title = models.CharField(max_length=255, help_text="Event title")
    slug = models.SlugField(max_length=300, unique=True, blank=True, help_text="URL-friendly identifier")
    description = models.TextField(help_text="Detailed event description (supports rich text)")
    short_description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Brief summary for preview cards"
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default='OTHER',
        help_text="Type of event"
    )
    event_image = models.ImageField(
        upload_to=event_image_upload_path,
        blank=True,
        null=True,
        help_text="Event banner/poster image"
    )

    # Event Timing
    start_datetime = models.DateTimeField(help_text="Event start date and time")
    end_datetime = models.DateTimeField(help_text="Event end date and time")
    registration_deadline = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last date to register (if different from event start)"
    )

    # Location Details
    is_online = models.BooleanField(default=False, help_text="Is this an online event?")
    venue_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Venue/Location name"
    )
    venue_address = models.TextField(blank=True, help_text="Full venue address")
    google_maps_link = models.URLField(
        blank=True,
        null=True,
        help_text="Google Maps link for the venue"
    )
    meeting_link = models.URLField(
        blank=True,
        null=True,
        help_text="Meeting link for online events (Zoom, Meet, Teams, etc.)"
    )

    # Registration Details
    max_participants = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum number of participants (leave blank for unlimited)"
    )
    registration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Registration fee (0 for free events)"
    )
    is_registration_open = models.BooleanField(
        default=True,
        help_text="Is registration currently open?"
    )

    # Event Details
    prizes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Prize information as JSON (e.g., {1st: 10000, 2nd: 5000})"
    )
    rules = models.TextField(blank=True, help_text="Event rules and regulations")
    eligibility_criteria = models.TextField(
        blank=True,
        help_text="Who can participate in this event"
    )
    schedule = models.JSONField(
        default=list,
        blank=True,
        help_text="Event schedule as JSON array"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Event tags for search and filtering"
    )

    # Contact Information
    contact_person = models.CharField(
        max_length=255,
        blank=True,
        help_text="Contact person name"
    )
    contact_email = models.EmailField(blank=True, help_text="Contact email")
    contact_phone = models.CharField(max_length=15, blank=True, help_text="Contact phone number")

    # Status & Publishing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Event status"
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Is this event visible to public?"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured events appear prominently"
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events',
        help_text="User who created this event"
    )
    view_count = models.IntegerField(default=0, help_text="Number of views")

    class Meta:
        ordering = ['-start_datetime']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['start_datetime', 'is_published']),
            models.Index(fields=['event_type', 'is_published']),
        ]

    def __str__(self):
        return f"{self.title} - {self.organization.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            # Ensure unique slug
            counter = 1
            while Event.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"/events/{self.slug}/"

    @property
    def is_past(self):
        """Check if event has ended"""
        return self.end_datetime < timezone.now()

    @property
    def is_ongoing(self):
        """Check if event is currently happening"""
        now = timezone.now()
        return self.start_datetime <= now <= self.end_datetime

    @property
    def is_upcoming(self):
        """Check if event is in the future"""
        return self.start_datetime > timezone.now()

    @property
    def registration_closed(self):
        """Check if registration is closed"""
        if not self.is_registration_open:
            return True
        if self.registration_deadline:
            return timezone.now() > self.registration_deadline
        return self.is_past

    @property
    def is_full(self):
        """Check if event has reached max participants"""
        if not self.max_participants:
            return False
        return self.registered_count >= self.max_participants

    @property
    def registered_count(self):
        """Get total number of registered participants"""
        return self.registrations.filter(status__in=['REGISTERED', 'CONFIRMED']).count()

    @property
    def present_count(self):
        """Get number of participants marked present"""
        return self.registrations.filter(attendance_status='PRESENT').count()

    @property
    def spots_remaining(self):
        """Get number of spots remaining"""
        if not self.max_participants:
            return None
        return max(0, self.max_participants - self.registered_count)

    def can_register(self, user):
        """Check if a user can register for this event"""
        if not self.is_published or self.registration_closed or self.is_full:
            return False
        # Check if already registered
        return not self.registrations.filter(
            user=user,
            status__in=['REGISTERED', 'CONFIRMED']
        ).exists()


class EventRegistration(BaseModel):
    """
    Model for user registrations to events.
    Tracks registration status and attendance.
    """
    REGISTRATION_STATUS_CHOICES = [
        ('REGISTERED', 'Registered'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('WAITLIST', 'Waitlisted'),
    ]

    ATTENDANCE_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations',
        help_text="Event for this registration"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_registrations',
        help_text="User who registered"
    )
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique registration number"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=REGISTRATION_STATUS_CHOICES,
        default='REGISTERED',
        help_text="Registration status"
    )
    attendance_status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='PENDING',
        help_text="Attendance status"
    )

    # Additional Information
    additional_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom form data (team name, special requirements, etc.)"
    )
    
    # Attendance Tracking
    marked_present_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances',
        help_text="Organizer who marked attendance"
    )
    marked_present_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When attendance was marked"
    )

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-created_at']
        verbose_name = 'Event Registration'
        verbose_name_plural = 'Event Registrations'
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['registration_number']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.event.title} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.registration_number:
            # Generate unique registration number
            event_code = self.event.slug[:8].upper().replace('-', '')
            unique_id = uuid.uuid4().hex[:6].upper()
            self.registration_number = f"{event_code}-{unique_id}"
        super().save(*args, **kwargs)

    def mark_present(self, marked_by):
        """Mark this registration as present"""
        self.attendance_status = 'PRESENT'
        self.marked_present_by = marked_by
        self.marked_present_at = timezone.now()
        self.save()

    def mark_absent(self):
        """Mark this registration as absent"""
        self.attendance_status = 'ABSENT'
        self.marked_present_by = None
        self.marked_present_at = None
        self.save()


class ManualParticipant(BaseModel):
    """
    Model for manually added participants (guests, walk-ins, etc.)
    These participants don't have user accounts but need certificates.
    """
    ATTENDANCE_STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='manual_participants',
        help_text="Event this participant attended"
    )
    
    # Participant Information
    name = models.CharField(max_length=255, help_text="Full name")
    email = models.EmailField(help_text="Email address")
    phone = models.CharField(max_length=15, blank=True, help_text="Phone number")
    organization_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="External organization/institution name"
    )
    designation = models.CharField(
        max_length=255,
        blank=True,
        help_text="Role/title/designation"
    )
    
    # Attendance
    attendance_status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='PRESENT',
        help_text="Attendance status"
    )
    
    # Metadata
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_manual_participants',
        help_text="Organizer who added this participant"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this participant"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Manual Participant'
        verbose_name_plural = 'Manual Participants'
        indexes = [
            models.Index(fields=['event', 'attendance_status']),
        ]

    def __str__(self):
        return f"{self.name} - {self.event.title} (Manual)"
