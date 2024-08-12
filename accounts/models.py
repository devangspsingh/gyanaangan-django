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

from courses.models import Course, Resource, Subject, Stream, SpecialPage


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

    def save(self, *args, **kwargs):
        # Check if the image URL has changed
        if self.img_google_url:
            if (
                not self.pk
                or not Profile.objects.filter(
                    pk=self.pk, img_google_url=self.img_google_url
                ).exists()
            ):
                # Download the image from the new Google URL
                response = requests.get(self.img_google_url)
                img_temp = ContentFile(response.content)

                # Save the image temporarily
                temp_image = BytesIO(img_temp.read())
                temp_image.seek(0)
                image = Image.open(temp_image)

                # Resize the image if necessary (e.g., to 300x300)
                if image.height > 300 or image.width > 300:
                    output_size = (300, 300)
                    image.thumbnail(output_size)

                # Save the processed image to the model
                image_io = BytesIO()
                image.save(image_io, format="JPEG")
                self.profile_pic.save(
                    f"{self.user.username}_profile_pic.jpg",
                    ContentFile(image_io.getvalue()),
                    save=False,
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} Profile"


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribed_users",
    )
    special_page = models.ForeignKey(
        SpecialPage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribed_users",
    )
    stream = models.ForeignKey(
        Stream,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribed_users",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribed_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        subscription_name = (
            self.course.name
            if self.course
            else (
                self.stream.name
                if self.stream
                else (
                    self.subject.name
                    if self.subject
                    else (self.special_page if self.special_page else "Unknown")
                )
            )
        )
        return f"{self.user.username} - {subscription_name}"

    @staticmethod
    def is_subscribed(user, course=None, stream=None, subject=None, special_page=None):
        return Subscription.objects.filter(
            user=user,
            course=course,
            stream=stream,
            subject=subject,
            special_page=special_page,
        ).exists()

    @staticmethod
    def subscribe(user, course=None, stream=None, subject=None, special_page=None):
        if not Subscription.is_subscribed(user, course, stream, subject, special_page):
            subscription = Subscription(
                user=user,
                course=course,
                stream=stream,
                subject=subject,
                special_page=special_page,
            )
            subscription.save()

    @staticmethod
    def unsubscribe(user, course=None, stream=None, subject=None, special_page=None):
        Subscription.objects.filter(
            user=user,
            course=course,
            stream=stream,
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
