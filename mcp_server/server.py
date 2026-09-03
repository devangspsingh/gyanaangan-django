import os
from starlette.responses import JSONResponse, HTMLResponse, Response
from asgiref.sync import sync_to_async

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .tools import register_tools
from . import blog_operations

MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

# Initialize MCPServer instance
mcp_server = MCPServer(
    name="gyanaangan-blog-mcp",
    version="0.2.0",
    instructions="Manage, scan, filter, read, update, draft, and publish GyanAangan blog posts."
)

# Register all tools
register_tools(mcp_server)

# Create underlying Streamable HTTP app (handles MCP JSON-RPC protocol)
_streamable_app = mcp_server.streamable_http_app(
    streamable_http_path="/mcp",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)
)

async def mcp_asgi_app(scope, receive, send):
    """Unified ASGI entrypoint for Django routing /mcp and /sse."""
    if scope["type"] == "lifespan":
        await _streamable_app(scope, receive, send)
        return

    if scope["type"] != "http":
        await _streamable_app(scope, receive, send)
        return

    path = scope.get("path", "")
    method = scope.get("method", "GET")

    async def send_with_cors(response: Response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, HEAD, OPTIONS, DELETE"
        response.headers["Access-Control-Allow-Headers"] = "*"
        await response(scope, receive, send)

    # 1. CORS Preflight
    if method == "OPTIONS":
        res = Response(status_code=204)
        await send_with_cors(res)
        return

    # 2. HEAD Probe (Essential for Google Gemini MCP validation)
    if method == "HEAD":
        res = Response(
            status_code=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        await send_with_cors(res)
        return

    # 3. Health check endpoint (/mcp/health)
    if path in ["/mcp/health", "/health"]:
        try:
            stats = await sync_to_async(blog_operations.get_blog_stats)()
            res = JSONResponse({
                "status": "healthy",
                "mcp_server": "gyanaangan-blog-mcp",
                "version": "0.2.0",
                "django_embedded": True,
                "stats": stats,
                "auth_required": bool(MCP_AUTH_TOKEN)
            })
        except Exception as e:
            res = JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=500)
        await send_with_cors(res)
        return

    # 4. Token & OAuth2 Authentication
    headers = dict(scope.get("headers", []))
    auth_header = headers.get(b"authorization", b"").decode("latin-1")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "token=" in scope.get("query_string", b"").decode("latin-1"):
        import urllib.parse
        qs = urllib.parse.parse_qs(scope.get("query_string", b"").decode("latin-1"))
        token = qs.get("token", [""])[0]

    is_authenticated = False
    if MCP_AUTH_TOKEN and token == MCP_AUTH_TOKEN:
        is_authenticated = True
    elif token:
        try:
            from oauth2_provider.models import AccessToken
            from django.utils import timezone
            def check_oauth(tok):
                return AccessToken.objects.filter(token=tok, expires__gt=timezone.now()).exists()
            is_authenticated = await sync_to_async(check_oauth)(token)
        except Exception:
            pass

    if (MCP_AUTH_TOKEN or token) and not is_authenticated:
        res = JSONResponse(
            {"error": "Unauthorized. Please provide a valid Bearer or OAuth token."},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'}
        )
        await send_with_cors(res)
        return

    # 5. Route to MCP Streamable App
    # Ensure the inner app receives path '/mcp'
    new_scope = dict(scope)
    new_scope["path"] = "/mcp"
    new_scope["raw_path"] = b"/mcp"
    await _streamable_app(new_scope, receive, send)
