"""ASGI routing for the single learnmcp process.

    /s/{token}/mcp  -> MCP Streamable HTTP app (token resolved per tool call)
    everything else -> Django
    lifespan        -> MCP app (starts the MCP session manager)
"""

import json
import re
import time
from collections import deque

from learn.context import STATE_CLIENT_KEY, STATE_TOKEN_KEY, current_client, current_token, detect_client
from learn.services.tokens import looks_like_token

MCP_PATH_RE = re.compile(r"^/s/([^/]+)/mcp/?$")


class RateLimiter:
    """In-memory sliding window per key (per process). Good enough for a pilot."""

    def __init__(self, limit_per_minute: int, window: float = 60.0):
        self.limit = limit_per_minute
        self.window = window
        self._hits: dict[str, deque] = {}
        self._last_sweep = time.monotonic()

    def allow(self, key: str) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        if now - self._last_sweep > self.window:
            self._sweep(now)
        return True

    def _sweep(self, now: float) -> None:
        self._last_sweep = now
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]:
            del self._hits[key]


async def _send_json(send, status: int, payload: dict, headers: list | None = None) -> None:
    body = json.dumps(payload).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
            + (headers or []),
        }
    )
    await send({"type": "http.response.body", "body": body})


class TokenMiddleware:
    """Strip /s/{token} from the path and expose the token to the MCP tools."""

    def __init__(self, app, rate_limiter: RateLimiter | None = None):
        self.app = app
        self.rate_limiter = rate_limiter

    async def __call__(self, scope, receive, send, token: str):
        if not looks_like_token(token):
            await _send_json(send, 404, {"error": "Unknown learnmcp connection URL."})
            return
        if self.rate_limiter and not self.rate_limiter.allow(token):
            await _send_json(
                send, 429, {"error": "Too many requests. Please slow down."}, headers=[(b"retry-after", b"60")]
            )
            return

        headers = dict(scope.get("headers") or [])
        client = detect_client(headers.get(b"user-agent", b"").decode("latin-1"))
        state = dict(scope.get("state") or {})
        state[STATE_TOKEN_KEY] = token
        state[STATE_CLIENT_KEY] = client
        inner = dict(scope, path="/mcp", raw_path=b"/mcp", root_path="", state=state)

        tok_reset = current_token.set(token)
        cli_reset = current_client.set(client)
        try:
            await self.app(inner, receive, send)
        finally:
            current_token.reset(tok_reset)
            current_client.reset(cli_reset)


class LearnMCPRouter:
    def __init__(self, mcp_app, django_app, rate_limiter: RateLimiter | None = None):
        self.mcp_app = mcp_app
        self.django_app = django_app
        self.token_middleware = TokenMiddleware(mcp_app, rate_limiter)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.mcp_app(scope, receive, send)
            return
        if scope["type"] == "http":
            match = MCP_PATH_RE.match(scope.get("path", ""))
            if match:
                await self.token_middleware(scope, receive, send, token=match.group(1))
                return
        await self.django_app(scope, receive, send)
