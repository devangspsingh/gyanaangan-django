# Generated by Django 5.0.7 on 2024-08-03 16:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0017_remove_advertisement_image_remove_course_image_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resource',
            old_name='title',
            new_name='name',
        ),
    ]
