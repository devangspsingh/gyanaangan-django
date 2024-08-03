# Generated by Django 5.0.7 on 2024-08-02 14:20

import django.db.models.deletion
import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_year_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpecialPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=10)),
                ('description', models.TextField(blank=True)),
                ('meta_description', models.CharField(blank=True, max_length=160)),
                ('keywords', models.CharField(blank=True, max_length=200)),
                ('image', models.ImageField(blank=True, null=True, upload_to='images/')),
                ('course', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='special_page', to='courses.course')),
                ('notifications', models.ManyToManyField(blank=True, related_name='special_pages', to='courses.notification')),
                ('stream', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='special_page', to='courses.stream')),
                ('year', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='special_page', to='courses.year')),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('published', django.db.models.manager.Manager()),
            ],
        ),
    ]