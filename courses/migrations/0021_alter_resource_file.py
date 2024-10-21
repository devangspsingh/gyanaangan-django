# Generated by Django 5.0.7 on 2024-10-21 12:28

import gyanaangan.settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0020_alter_advertisement_options_alter_course_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='file',
            field=models.FileField(blank=True, null=True, storage=gyanaangan.settings.PrivateMediaStorage, upload_to='resources/'),
        ),
    ]
