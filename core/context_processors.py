from .models import SEODetail
from django.templatetags.static import static

def seo_defaults(request):
    default_og_image_url = static('images/default-og-image.jpg')
    try:
        seo_detail = SEODetail.objects.get(page_name='default')
    except SEODetail.DoesNotExist:
        seo_detail = SEODetail(
            page_name='default',
            title='Welcome to Gyan Aangan',
            meta_description='Browse a variety of courses, subjects, and resources to enhance your knowledge.',
            site_name='Gyan Aangan'
        )
    
    return {
        'default_title': seo_detail.title,
        'default_meta_description': seo_detail.meta_description,
        'default_og_image': seo_detail.og_image.url if seo_detail.og_image else '/static/images/default-og-image.png',
        'default_site_name': seo_detail.site_name,
        'default_full_title': f'{seo_detail.title}',
    }
