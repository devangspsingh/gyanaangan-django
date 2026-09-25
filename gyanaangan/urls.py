from django.conf import settings
from django.conf.urls.static import static
from django.templatetags.static import static as STATIC
from django.urls import path, include
from django.contrib import admin
from django.views.generic import RedirectView
from oauth2_provider import views as oauth2_views
from mcp_server.views import (
    oauth_authorization_server_discovery,
    oauth_protected_resource_metadata,
    AutoApproveAuthorizationView,
    mcp_http_view,
)


urlpatterns = (
    [
        path("admin/", admin.site.urls, name="admin"),
        path("results/", include("results.urls")),
        path("api/", include("api.urls")),
        path("blog/", include("blog.urls")),
        path("accounts/", include("accounts.urls")),
        path("core/", include("core.urls")),
        path("ads.txt", RedirectView.as_view(url=STATIC("ads.txt"), permanent=True)),
        path("", include("courses.urls")),
        path("ckeditor/", include("ckeditor_uploader.urls")),
        path("__reload__/", include("django_browser_reload.urls")),

        # Model Context Protocol (MCP) Streamable HTTP & SSE Endpoints
        path("mcp", mcp_http_view),
        path("mcp/", mcp_http_view),
        path("api/mcp", mcp_http_view),
        path("api/mcp/", mcp_http_view),
        path("sse", mcp_http_view),
        path("sse/", mcp_http_view),
        path("api/sse", mcp_http_view),
        path("api/sse/", mcp_http_view),

        # Google Gemini, ChatGPT & Claude OAuth 2.0 Endpoints
        path("o/authorize/", AutoApproveAuthorizationView.as_view(), name="authorize"),
        path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
        path("authorize/", AutoApproveAuthorizationView.as_view()),
        path("authorize", AutoApproveAuthorizationView.as_view()),
        path("token/", oauth2_views.TokenView.as_view()),
        path("token", oauth2_views.TokenView.as_view()),
        path("api/authorize/", AutoApproveAuthorizationView.as_view()),
        path("api/authorize", AutoApproveAuthorizationView.as_view()),
        path("api/token/", oauth2_views.TokenView.as_view()),
        path("api/token", oauth2_views.TokenView.as_view()),
        path("api/o/authorize/", AutoApproveAuthorizationView.as_view()),
        path("api/o/token/", oauth2_views.TokenView.as_view()),
        path("api/o/revoke_token/", oauth2_views.RevokeTokenView.as_view()),

        # RFC 8414 & RFC 9449 Discovery Endpoints
        path(".well-known/oauth-authorization-server", oauth_authorization_server_discovery),
        path(".well-known/oauth-protected-resource/mcp", oauth_protected_resource_metadata),
        path(".well-known/oauth-protected-resource", oauth_protected_resource_metadata),
        path("api/.well-known/oauth-authorization-server", oauth_authorization_server_discovery),
        path("api/.well-known/oauth-protected-resource/mcp", oauth_protected_resource_metadata),
        path("api/.well-known/oauth-protected-resource", oauth_protected_resource_metadata),
    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)

handler404 = "core.views.custom_page_not_found_view"
handler500 = "core.views.custom_error_view"
handler403 = "core.views.custom_permission_denied_view"
handler400 = "core.views.custom_bad_request_view"


admin.site.site_header = "Gyan Aangan Administration"
admin.site.site_title = "Gyan Aangane Admin Portal"
admin.site.index_title = "Welcome to Gyan Aangan"
