# Generated by Django 5.0.7 on 2024-08-04 09:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seodetail',
            name='page_name',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
