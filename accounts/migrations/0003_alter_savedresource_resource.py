# Generated by Django 5.0.7 on 2024-08-11 13:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_savedresource_subscription'),
        ('courses', '0020_alter_advertisement_options_alter_course_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='savedresource',
            name='resource',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.resource'),
        ),
    ]
