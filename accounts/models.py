import os
import uuid
from django.db import models
from django.conf import settings
from PIL import Image
from django.db.models.signals import post_save
from django.dispatch import receiver
from io import BytesIO
from django.core.files.base import ContentFile
import requests
from django.db.models import Max
from courses.models import Course, Resource, Subject, Stream, SpecialPage, Year


def profile_pic_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("profile_pics/", filename)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(
        upload_to=profile_pic_upload_path, default="default.jpg"
    )
    emoji_tag = models.CharField(max_length=5, blank=True)
    img_google_url = models.URLField(max_length=500, blank=True, null=True)
    is_profile_public = models.BooleanField(default=True, help_text="Whether the user's profile is publicly visible")

    def save(self, *args, **kwargs):
        if not self.pk:  # If this is a new profile
            last_id = Profile.objects.aggregate(Max("id"))["id__max"]
            self.id = (last_id or 0) + 1

        if self.img_google_url:
            if (not self.pk or not Profile.objects.filter(pk=self.pk, img_google_url=self.img_google_url).exists()):
                # Download the image from the new Google URL
                response = requests.get(self.img_google_url)
                img_temp = ContentFile(response.content)

                # Save the image temporarily
                temp_image = BytesIO(img_temp.read())
                temp_image.seek(0)
                image = Image.open(temp_image)

                # Handle GIF separately
                if image.format == "GIF":
                    self.profile_pic.save(
                        f"{self.user.username}_profile_pic.gif",
                        ContentFile(response.content),
                        save=False,
                    )
                else:
                    # Convert RGBA to RGB if necessary
                    if image.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', image.size, (255, 255, 255))
                        background.paste(image, mask=image.split()[-1])
                        image = background
                    elif image.mode != 'RGB':
                        image = image.convert('RGB')

                    # Resize if necessary
                    if image.height > 300 or image.width > 300:
                        output_size = (300, 300)
                        image.thumbnail(output_size)

                    # Save as JPEG
                    image_io = BytesIO()
                    image.save(image_io, format="JPEG", quality=85)
                    self.profile_pic.save(
                        f"{self.user.username}_profile_pic.jpg",
                        ContentFile(image_io.getvalue()),
                        save=False,
                    )

        super().save(*args, **kwargs)
        def __str__(self):
            return f"{self.user.username} Profile"


class Subscription(models.Model):
    """
    Subscription model for users to subscribe to courses, subjects, or special pages.
    Note: special_page already contains course, stream, and year information.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    # For subscribing to individual courses (without specific stream/year)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribed_users",
    )
    # For subscribing to specific course/stream/year combinations
    special_page = models.ForeignKey(
        SpecialPage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribed_users",
    )
    # For subscribing to individual subjects
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribed_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure unique subscriptions per user for each type
        unique_together = [['user', 'course', 'subject', 'special_page']]

    def __str__(self):
        if self.special_page:
            return f"{self.user.username} - {self.special_page.course.name}/{self.special_page.stream.name}/{self.special_page.year.name}"
        elif self.course:
            return f"{self.user.username} - {self.course.name}"
        elif self.subject:
            return f"{self.user.username} - {self.subject.name}"
        return f"{self.user.username} - Unknown"

    @staticmethod
    def is_subscribed(user, course=None, subject=None, special_page=None):
        return Subscription.objects.filter(
            user=user,
            course=course,
            subject=subject,
            special_page=special_page,
        ).exists()

    @staticmethod
    def subscribe(user, course=None, subject=None, special_page=None):
        if not Subscription.is_subscribed(user, course, subject, special_page):
            subscription = Subscription(
                user=user,
                course=course,
                subject=subject,
                special_page=special_page,
            )
            subscription.save()
            return subscription
        return None

    @staticmethod
    def unsubscribe(user, course=None, subject=None, special_page=None):
        Subscription.objects.filter(
            user=user,
            course=course,
            subject=subject,
            special_page=special_page,
        ).delete()


class SavedResource(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="saved_resources",
        on_delete=models.CASCADE,
    )
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def is_resource_saved(user, resource):
        return SavedResource.objects.filter(user=user, resource=resource).exists()


class StudentProfile(models.Model):
    """
    Extended profile for students with academic information
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    
    # Academic Information
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrolled_students')
    stream = models.ForeignKey(Stream, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrolled_students')
    year = models.ForeignKey(Year, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrolled_students')
    
    # Additional Information
    college_name = models.CharField(max_length=255, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    year_of_graduation = models.IntegerField(blank=True, null=True, help_text="Expected year of graduation")
    
    # Metadata
    is_profile_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Student Profile"
    
    def save(self, *args, **kwargs):
        # Check if profile is complete
        if self.course and self.stream and self.year:
            self.is_profile_complete = True
        else:
            self.is_profile_complete = False
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
