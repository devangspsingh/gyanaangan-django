# Generated by Django 5.0.7 on 2024-07-15 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_subject_years'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='last_resource_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]