from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def oauth_authorization_server_discovery(request):
    """RFC 8414 OAuth 2.0 Authorization Server Metadata."""
    base_url = f"{request.scheme}://{request.get_host()}"
    return JsonResponse({
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/o/authorize/",
        "token_endpoint": f"{base_url}/o/token/",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": ["read", "write", "mcp", "offline_access", "openid", "email", "profile", "user"]
    })

@require_GET
def oauth_protected_resource_metadata(request):
    """RFC 9449 OAuth 2.0 Protected Resource Metadata."""
    base_url = f"{request.scheme}://{request.get_host()}"
    return JsonResponse({
        "resource": f"{base_url}/mcp",
        "authorization_servers": [base_url],
        "scopes_supported": ["read", "write", "mcp", "offline_access", "openid", "email", "profile", "user"]
    })

from oauth2_provider.views import AuthorizationView
from django.contrib.auth import get_user_model, login

User = get_user_model()

class AutoApproveAuthorizationView(AuthorizationView):
    """
    Subclasses OAuth2 AuthorizationView.
    If the user isn't logged in to the browser session, automatically logs in the
    primary active superuser so Google Gemini / MCP account linking can proceed
    seamlessly without demanding a login screen.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            user = User.objects.filter(is_superuser=True, is_active=True).first()
            if not user:
                user = User.objects.filter(is_staff=True, is_active=True).first()
            if user:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                request.user = user
        return super().dispatch(request, *args, **kwargs)

