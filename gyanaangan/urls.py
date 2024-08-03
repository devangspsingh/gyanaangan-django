from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('courses.urls')),
    path("__reload__/", include("django_browser_reload.urls")),
] + static(settings.MEDIA_URL) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    
    
