from django.db import models

from gyanaangan.settings import PublicMediaStorage

class SEODetail(models.Model):
    page_name = models.CharField(max_length=100, unique=True,blank=True,null=True)
    title = models.CharField(max_length=255)
    meta_description = models.TextField()
    og_image = models.ImageField(storage=PublicMediaStorage,upload_to='og_images/', blank=True, null=True)
    site_name = models.CharField(max_length=255, default='Gyan Aangan')

    def __str__(self):
        return self.title
