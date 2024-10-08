# Generated by Django 5.0.7 on 2024-07-20 10:56

import django.db.models.manager
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0008_rename_subjects_resource_subject_and_more'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='course',
            managers=[
                ('published', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='resource',
            managers=[
                ('published', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='stream',
            managers=[
                ('published', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='subject',
            managers=[
                ('published', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='year',
            managers=[
                ('published', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name='educationalyear',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='educationalyear',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=10),
        ),
        migrations.AddField(
            model_name='educationalyear',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
