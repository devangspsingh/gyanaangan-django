# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Resource, Subject

@receiver(post_save, sender=Resource)
def update_subject_last_resource_updated(sender, instance, **kwargs):
    if instance.subject:
        subject = instance.subject
        subject.update_last_resource_updated()
        subject.save()
