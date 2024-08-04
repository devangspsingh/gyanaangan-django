from django.contrib import admin
from .models import SEODetail

@admin.register(SEODetail)
class SEODetailAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'title', 'meta_description', 'og_image', 'site_name')
    search_fields = ('page_name', 'title')
