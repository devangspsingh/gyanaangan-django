from django import template
from django.urls import resolve

register = template.Library()

@register.inclusion_tag('breadcrumbs.html', takes_context=True)
def show_breadcrumbs(context):
    request = context['request']
    path = request.path.strip('/').split('/')
    breadcrumbs = []
    breadcrumb_url = ''

    for part in path:
        if part:
            breadcrumb_url += f'/{part}'
            try:
                resolved = resolve(breadcrumb_url)
                if resolved.url_name:
                    breadcrumbs.append({
                        'name': format_breadcrumb_name(part),
                        'url': breadcrumb_url
                    })
            except:
                breadcrumbs.append({
                    'name': format_breadcrumb_name(part),
                    'url': breadcrumb_url
                })

    return {'breadcrumbs': breadcrumbs}

def format_breadcrumb_name(part):
    if part[:3] in ['1st', '2nd', '3rd', '4th']:
        return part[:3] + part[3:].replace('-', ' ').replace('_', ' ').title()
    else:
        return part.replace('-', ' ').replace('_', ' ').title()
