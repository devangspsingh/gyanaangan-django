# Generated by Django 5.0.7 on 2024-08-01 16:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_alter_subject_stream'),
    ]

    operations = [
        migrations.AddField(
            model_name='year',
            name='name',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
