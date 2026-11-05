"""Per-request student identity for MCP tools.

The router puts the raw token and the detected client into the ASGI scope state
(read back through the MCP request context) and also into contextvars, which
tests use to call tools directly.
"""

from contextvars import ContextVar

STATE_TOKEN_KEY = "learnmcp_token"
STATE_CLIENT_KEY = "learnmcp_client"

current_token: ContextVar[str | None] = ContextVar("learnmcp_token", default=None)
current_client: ContextVar[str] = ContextVar("learnmcp_client", default="")


def detect_client(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "claude" in ua or "anthropic" in ua:
        return "claude"
    if "openai" in ua or "chatgpt" in ua:
        return "chatgpt"
    if "inspector" in ua:
        return "inspector"
    return "other" if ua else ""
