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
        "scopes_supported": ["read", "write"]
    })

@require_GET
def oauth_protected_resource_metadata(request):
    """RFC 9449 OAuth 2.0 Protected Resource Metadata."""
    base_url = f"{request.scheme}://{request.get_host()}"
    return JsonResponse({
        "resource": f"{base_url}/mcp",
        "authorization_servers": [base_url],
        "scopes_supported": ["read", "write"]
    })
