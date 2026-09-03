import os
from django.core.management.base import BaseCommand
import uvicorn
from mcp_server.server import mcp_asgi_app

class Command(BaseCommand):
    help = "Run the GyanAangan MCP server for Gemini Connected Apps"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            default="0.0.0.0",
            help="Bind host (default: 0.0.0.0)"
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Bind port (default: 8001)"
        )

    def handle(self, *args, **options):
        host = options["host"]
        port = options["port"]
        auth_token = os.getenv("MCP_AUTH_TOKEN", "")

        self.stdout.write(self.style.SUCCESS(f"🚀 Starting GyanAangan Blog MCP Server on http://{host}:{port}"))
        self.stdout.write(f"👉 Gemini MCP Endpoint: http://{host}:{port}/mcp (or /sse)")
        self.stdout.write(f"👉 Health check: http://{host}:{port}/mcp/health")
        if auth_token:
            self.stdout.write(self.style.WARNING("🔒 Authentication: Enabled (Bearer token required)"))
        else:
            self.stdout.write(self.style.NOTICE("🔓 Authentication: None (Public access)"))

        uvicorn.run(mcp_asgi_app, host=host, port=port, log_level="info")
