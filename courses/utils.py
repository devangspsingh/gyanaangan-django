# utils.py
from django.db.models.signals import post_save
from contextlib import contextmanager

@contextmanager
def disable_signal(signal, sender, receiver):
    signal.disconnect(receiver, sender=sender)
    yield
    signal.connect(receiver, sender=sender)
