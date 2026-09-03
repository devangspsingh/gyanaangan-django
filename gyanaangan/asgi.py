"""
ASGI config for gyanaangan project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gyanaangan.settings')

django_asgi_app = get_asgi_application()

from mcp_server.server import mcp_asgi_app

async def application(scope, receive, send):
    """
    ASGI application dispatcher:
    Routes /mcp and /sse to the GyanAangan MCP server,
    and all other traffic to Django.
    """
    if scope["type"] == "http":
        path = scope.get("path", "")
        if path.startswith("/mcp") or path.startswith("/sse"):
            await mcp_asgi_app(scope, receive, send)
            return

    await django_asgi_app(scope, receive, send)
