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

def profile_pic_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("profile_pics/", filename)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to=profile_pic_upload_path, default="default.jpg")
    emoji_tag = models.CharField(max_length=5, blank=True)
    img_google_url = models.URLField(max_length=500, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Check if the image URL has changed
        if self.img_google_url:
            if not self.pk or not Profile.objects.filter(pk=self.pk, img_google_url=self.img_google_url).exists():
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
                image.save(image_io, format='JPEG')
                self.profile_pic.save(f"{self.user.username}_profile_pic.jpg", ContentFile(image_io.getvalue()), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} Profile"
