from django import template

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """Template filter to look up dictionary values"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''


@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def get_subject_marks(marks_data, subject_code):
    """Get marks for a specific subject"""
    if isinstance(marks_data, dict) and subject_code in marks_data:
        return marks_data[subject_code]
    return {}
