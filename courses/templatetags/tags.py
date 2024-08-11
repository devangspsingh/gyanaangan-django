
from django import template

from accounts.models import SavedResource

register = template.Library()

@register.filter()
def multiply(value, arg):
    return int(value) * int(arg)

@register.filter
def is_saved_by_user(resource, user):
    return SavedResource.is_resource_saved(user, resource)
