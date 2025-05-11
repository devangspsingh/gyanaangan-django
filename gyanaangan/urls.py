from django.conf import settings
from django.conf.urls.static import static
from django.templatetags.static import static as STATIC
from django.urls import path, include
from django.contrib import admin
from django.views.generic import RedirectView

print(static("ads.txt"))

urlpatterns = (
    [
        path("admin/", admin.site.urls, name="admin"),
        path("blog/", include("blog.urls")),
        path("api/", include("api.urls")),
        path("accounts/", include("accounts.urls")),
        path("core/", include("core.urls")),
        path("ads.txt", RedirectView.as_view(url=STATIC("ads.txt"), permanent=True)),
        # path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
        path("", include("courses.urls")),
        path("__reload__/", include("django_browser_reload.urls")),
        path("ckeditor/", include("ckeditor_uploader.urls")),
    ]
    + static(settings.MEDIA_URL)
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)

handler404 = "core.views.custom_page_not_found_view"
handler500 = "core.views.custom_error_view"
handler403 = "core.views.custom_permission_denied_view"
handler400 = "core.views.custom_bad_request_view"


admin.site.site_header = "Gyan Aangan Administration"
admin.site.site_title = "Gyan Aangane Admin Portal"
admin.site.index_title = "Welcome to Gyan Aangan"
