# Generated by Django 5.0.7 on 2024-08-01 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0012_stream_years'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subject',
            name='stream',
            field=models.ManyToManyField(blank=True, related_name='subjects', to='courses.stream'),
        ),
    ]
