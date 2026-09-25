import asyncio
import logging
import threading
import time
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.views import AuthorizationView
from oauth2_provider.models import get_application_model

logger = logging.getLogger(__name__)
User = get_user_model()
Application = get_application_model()


class AutoApproveAuthorizationView(AuthorizationView):
    """
    Subclasses OAuth2 AuthorizationView.
    - Dynamically auto-registers redirect URIs for trusted AI platforms (ChatGPT, Claude, Gemini).
    - If the user isn't logged in to the browser session, automatically logs in the
      primary active superuser so AI client account linking proceeds seamlessly.
    """
    def dispatch(self, request, *args, **kwargs):
        from django.db import close_old_connections
        close_old_connections()

        # Dynamically auto-register redirect_uri for trusted AI platforms (ChatGPT, Claude, Google)
        client_id = request.GET.get('client_id') or request.POST.get('client_id')
        redirect_uri = request.GET.get('redirect_uri') or request.POST.get('redirect_uri')
        if client_id and redirect_uri:
            parsed = urlsplit(redirect_uri)
            trusted_domains = ("chatgpt.com", "claude.ai", "googleusercontent.com", "cloud.google.com")
            if any(parsed.netloc == d or parsed.netloc.endswith("." + d) for d in trusted_domains):
                app = Application.objects.filter(client_id=client_id).first()
                if app:
                    current_uris = set(app.redirect_uris.split())
                    if redirect_uri not in current_uris:
                        app.redirect_uris = f"{app.redirect_uris} {redirect_uri}".strip()
                        app.save(update_fields=["redirect_uris"])
                        logger.info(f"Auto-registered redirect URI '{redirect_uri}' for application '{app.name}'.")

        if not request.user.is_authenticated:
            user = (
                User.objects.filter(is_superuser=True, is_active=True).first()
                or User.objects.filter(is_staff=True, is_active=True).first()
                or User.objects.filter(is_active=True).first()
            )
            if user:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                request.user = user
                logger.info(f"Auto-authenticated user '{user}' for AI OAuth flow.")

        return super().dispatch(request, *args, **kwargs)


@csrf_exempt
def oauth_authorization_server_discovery(request):
    """RFC 8414 OAuth 2.0 Authorization Server Metadata."""
    scheme = "https" if request.is_secure() or request.headers.get("X-Forwarded-Proto") == "https" else "http"
    base_url = f"{scheme}://{request.get_host()}"
    data = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/o/authorize/",
        "token_endpoint": f"{base_url}/o/token/",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": ["read", "write", "mcp", "offline_access", "openid", "email", "profile", "user"],
    }
    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    return response


@csrf_exempt
def oauth_protected_resource_metadata(request):
    """RFC 9449 OAuth 2.0 Protected Resource Metadata."""
    scheme = "https" if request.is_secure() or request.headers.get("X-Forwarded-Proto") == "https" else "http"
    base_url = f"{scheme}://{request.get_host()}"
    data = {
        "resource": f"{base_url}/mcp",
        "authorization_servers": [base_url],
        "scopes_supported": ["read", "write", "mcp", "offline_access", "openid", "email", "profile", "user"],
        "bearer_methods_supported": ["header"],
    }
    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    return response


# ---------------------------------------------------------------------------
# MCPServer WSGI / HTTP Bridge View
# ---------------------------------------------------------------------------
_mcp_loop = None
_mcp_thread = None


def _get_mcp_event_loop():
    global _mcp_loop, _mcp_thread
    if _mcp_loop is None or not _mcp_loop.is_running():
        _mcp_loop = asyncio.new_event_loop()

        def _run():
            asyncio.set_event_loop(_mcp_loop)
            _mcp_loop.run_forever()

        _mcp_thread = threading.Thread(target=_run, daemon=True, name="gyanaangan-mcp-worker")
        _mcp_thread.start()
        time.sleep(0.1)
    return _mcp_loop


@csrf_exempt
def mcp_http_view(request):
    """
    HTTP View bridging ChatGPT, Gemini, and Claude MCP requests
    directly into the MCPServer ASGI application in WSGI or ASGI environments.
    """
    from django.db import close_old_connections
    close_old_connections()

    if request.method == "OPTIONS":
        resp = HttpResponse(status=204)
        resp["Access-Control-Allow-Origin"] = "*"
        resp["Access-Control-Allow-Methods"] = "GET, POST, HEAD, OPTIONS, DELETE"
        resp["Access-Control-Allow-Headers"] = "*"
        return resp

    try:
        loop = _get_mcp_event_loop()
    except Exception as e:
        logger.error(f"Failed to initialize MCP event loop: {e}")
        return HttpResponse(b'{"jsonrpc":"2.0","error":{"code":-32603,"message":"Internal MCP Server Error"}}', status=500, content_type="application/json")

    headers = []
    for k, v in request.headers.items():
        headers.append((k.lower().encode("latin1"), v.encode("latin1")))

    scope = {
        "type": "http",
        "method": request.method,
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": request.META.get("QUERY_STRING", "").encode("utf-8"),
        "headers": headers,
    }

    body = request.body

    async def _handle():
        from mcp_server.server import mcp_asgi_app

        sent_start = False
        status_code = 200
        resp_headers = []
        chunks = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(msg):
            nonlocal sent_start, status_code, resp_headers
            if msg["type"] == "http.response.start":
                status_code = msg["status"]
                for k, v in msg.get("headers", []):
                    resp_headers.append((k.decode("latin1"), v.decode("latin1")))
                sent_start = True
            elif msg["type"] == "http.response.body":
                chunks.append(msg.get("body", b""))

        await mcp_asgi_app(scope, receive, send)
        return status_code, resp_headers, b"".join(chunks)

    try:
        future = asyncio.run_coroutine_threadsafe(_handle(), loop)
        status_code, resp_headers, res_body = future.result(timeout=60)
    except Exception as e:
        logger.exception(f"Error handling MCP request: {e}")
        resp = HttpResponse(b'{"jsonrpc":"2.0","error":{"code":-32603,"message":"MCP bridge error"}}', status=500, content_type="application/json")
        resp["Access-Control-Allow-Origin"] = "*"
        return resp

    response = HttpResponse(content=res_body, status=status_code)
    for k, v in resp_headers:
        k_lower = k.lower()
        if k_lower not in ("content-length", "content-type"):
            response[k] = v
        elif k_lower == "content-type":
            response["Content-Type"] = v

    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Headers"] = "*"
    return response
