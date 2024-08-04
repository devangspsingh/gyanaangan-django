# Generated by Django 5.0.7 on 2024-08-04 08:01

import gyanaangan.settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0018_rename_title_resource_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advertisement',
            name='og_image',
            field=models.FileField(blank=True, null=True, storage=gyanaangan.settings.PublicMediaStorage(), upload_to='og-image/'),
        ),
        migrations.AlterField(
            model_name='course',
            name='og_image',
            field=models.FileField(blank=True, null=True, storage=gyanaangan.settings.PublicMediaStorage(), upload_to='og-image/'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='file',
            field=models.FileField(storage=gyanaangan.settings.PrivateMediaStorage, upload_to='resources/'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='og_image',
            field=models.FileField(blank=True, null=True, storage=gyanaangan.settings.PublicMediaStorage(), upload_to='og-image/'),
        ),
        migrations.AlterField(
            model_name='specialpage',
            name='og_image',
            field=models.FileField(blank=True, null=True, storage=gyanaangan.settings.PublicMediaStorage(), upload_to='og-image/'),
        ),
        migrations.AlterField(
            model_name='stream',
            name='og_image',
            field=models.FileField(blank=True, null=True, storage=gyanaangan.settings.PublicMediaStorage(), upload_to='og-image/'),
        ),
        migrations.AlterField(
            model_name='subject',
            name='og_image',
            field=models.FileField(blank=True, null=True, storage=gyanaangan.settings.PublicMediaStorage(), upload_to='og-image/'),
        ),
    ]