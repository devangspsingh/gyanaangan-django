import os
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError


def organization_logo_upload_path(instance, filename):
    """Upload path for organization logos"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("organizations/logos/", filename)


def organization_cover_upload_path(instance, filename):
    """Upload path for organization cover images"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("organizations/covers/", filename)


def organization_gallery_upload_path(instance, filename):
    """Upload path for organization gallery images"""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"organizations/{instance.organization.slug}/gallery/", filename)


class BaseModel(models.Model):
    """Base model with common timestamp fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(BaseModel):
    """
    Model for organizations/clubs that can host events.
    Each organization has a creator and can have multiple members with different roles.
    """
    name = models.CharField(max_length=255, unique=True, help_text="Organization name")
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly identifier")
    description = models.TextField(blank=True, help_text="About the organization")
    logo = models.ImageField(
        upload_to=organization_logo_upload_path,
        blank=True,
        null=True,
        help_text="Organization logo"
    )
    cover_image = models.ImageField(
        upload_to=organization_cover_upload_path,
        blank=True,
        null=True,
        help_text="Organization banner/cover image"
    )
    
    # Contact Information
    contact_email = models.EmailField(blank=True, help_text="Official contact email")
    contact_phone = models.CharField(max_length=15, blank=True, help_text="Contact phone number")
    website = models.URLField(blank=True, null=True, help_text="Organization website")
    
    # Social Media Links (stored as JSON)
    social_links = models.JSONField(
        default=dict,
        blank=True,
        help_text="Social media links (Facebook, Instagram, LinkedIn, Twitter, etc.)"
    )
    
    # Metadata
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this organization is verified by admin"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this organization is active"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_organizations',
        help_text="User who created this organization"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_verified', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while Organization.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"/organizations/{self.slug}/"

    @property
    def member_count(self):
        """Get total number of active members"""
        return self.members.filter(is_active=True).count()

    @property
    def admin_count(self):
        """Get number of admins"""
        return self.members.filter(role='ADMIN', is_active=True).count()

    def has_member(self, user):
        """Check if user is a member of this organization"""
        return self.members.filter(user=user, is_active=True).exists()

    def get_user_role(self, user):
        """Get the role of a user in this organization"""
        try:
            member = self.members.get(user=user, is_active=True)
            return member.role
        except OrganizationMember.DoesNotExist:
            return None

    def is_admin(self, user):
        """Check if user is an admin of this organization"""
        return self.members.filter(user=user, role='ADMIN', is_active=True).exists()


class OrganizationMember(BaseModel):
    """
    Model for organization members with role-based permissions.
    Supports ADMIN, MEMBER, and VIEWER roles.
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MEMBER', 'Member'),
        ('VIEWER', 'Viewer'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members',
        help_text="Organization this member belongs to"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
        help_text="User who is a member"
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='MEMBER',
        help_text="Role of the member in the organization"
    )
    
    # Custom Permissions (JSON field for flexibility)
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom permissions: can_create_events, can_edit_events, can_manage_members, etc."
    )
    
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_members',
        help_text="User who invited this member"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this membership is active"
    )

    class Meta:
        unique_together = ['organization', 'user']
        ordering = ['-joined_at']
        verbose_name = 'Organization Member'
        verbose_name_plural = 'Organization Members'
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['role', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"

    def clean(self):
        """Validate that organization has at least one admin"""
        if self.pk and not self.is_active and self.role == 'ADMIN':
            # Check if this is the last active admin
            active_admins = OrganizationMember.objects.filter(
                organization=self.organization,
                role='ADMIN',
                is_active=True
            ).exclude(pk=self.pk).count()
            
            if active_admins == 0:
                raise ValidationError("Organization must have at least one active admin.")

    def has_permission(self, permission_key):
        """
        Check if member has a specific permission.
        Admins have all permissions by default.
        """
        if self.role == 'ADMIN':
            return True
        return self.permissions.get(permission_key, False)

    @staticmethod
    def get_default_permissions(role):
        """Get default permissions based on role"""
        if role == 'ADMIN':
            return {
                'can_create_events': True,
                'can_edit_events': True,
                'can_delete_events': True,
                'can_manage_members': True,
                'can_edit_organization': True,
                'can_view_analytics': True,
            }
        elif role == 'MEMBER':
            return {
                'can_create_events': True,
                'can_edit_events': False,
                'can_delete_events': False,
                'can_manage_members': False,
                'can_edit_organization': False,
                'can_view_analytics': True,
            }
        else:  # VIEWER
            return {
                'can_create_events': False,
                'can_edit_events': False,
                'can_delete_events': False,
                'can_manage_members': False,
                'can_edit_organization': False,
                'can_view_analytics': False,
            }


class OrganizationGallery(BaseModel):
    """
    Model for organization gallery images.
    Organizations can showcase their activities through gallery images.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        help_text="Organization this image belongs to"
    )
    image = models.ImageField(
        upload_to=organization_gallery_upload_path,
        help_text="Gallery image"
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        help_text="Image caption or description"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Order in which to display (lower numbers first)"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_gallery_images',
        help_text="User who uploaded this image"
    )

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Organization Gallery Image'
        verbose_name_plural = 'Organization Gallery Images'
        indexes = [
            models.Index(fields=['organization', 'display_order']),
        ]

    def __str__(self):
        return f"{self.organization.name} - Gallery Image {self.id}"
