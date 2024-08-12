
from django import template

from accounts.models import SavedResource, Subscription
from courses.models import Course, SpecialPage, Stream, Subject

register = template.Library()

@register.filter()
def multiply(value, arg):
    return int(value) * int(arg)

@register.filter()
def is_saved_by_user(resource, user):
    return SavedResource.is_resource_saved(user, resource)

@register.filter()
def is_subscribed_to(entity, user):
    if user.is_authenticated:
        if isinstance(entity, SpecialPage):
            return Subscription.objects.filter(user=user, special_page=entity).exists()
        elif isinstance(entity, Subject):
            return Subscription.objects.filter(user=user, subject=entity).exists()
        elif isinstance(entity, Course):
            return Subscription.objects.filter(user=user, course=entity).exists()
        elif isinstance(entity, Stream):
            return Subscription.objects.filter(user=user, stream=entity).exists()

    return False