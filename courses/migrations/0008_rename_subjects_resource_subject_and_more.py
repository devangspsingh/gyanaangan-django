# Generated by Django 5.0.7 on 2024-07-19 07:55

import multiselectfield.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_resource_privacy'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resource',
            old_name='subjects',
            new_name='subject',
        ),
        migrations.AlterField(
            model_name='resource',
            name='privacy',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('download', 'Download'), ('view', 'View')], default=['view'], max_length=13),
        ),
    ]