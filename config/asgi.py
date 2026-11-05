"""ASGI entry point: one process serves Django (admin, student pages) and the MCP endpoint.

Run with:  uvicorn config.asgi:application
(`manage.py runserver` does not serve the MCP endpoint.)
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from learn.mcp_server import build_http_app  # noqa: E402
from learn.middleware import LearnMCPRouter, RateLimiter  # noqa: E402

django_app = get_asgi_application()
mcp_app = build_http_app()  # its lifespan runs the MCP session manager

application = LearnMCPRouter(
    mcp_app=mcp_app,
    django_app=django_app,
    rate_limiter=RateLimiter(settings.MCP_RATE_LIMIT_PER_MINUTE),
)
