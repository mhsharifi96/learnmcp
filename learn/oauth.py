"""Minimal auto-approving OAuth 2.1 server for MCP clients.

The real credential is the personal token in the connector URL (/s/{token}/mcp). Some clients
(claude.ai) still run OAuth discovery and Dynamic Client Registration when a connector is added
and fail if there is no authorization server. These endpoints satisfy that flow without a login
screen: registration always succeeds, /authorize redirects straight back with a code, and /token
issues an opaque access token that the MCP endpoint ignores.

Codes are stateless (signed with SECRET_KEY) and bind redirect_uri and the PKCE challenge.
"""

import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.core import signing
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

CODE_SALT = "learnmcp.oauth.code"
CODE_MAX_AGE = 600  # seconds
TOKEN_LIFETIME = 60 * 60 * 24 * 365


def _base_url(request) -> str:
    return settings.PUBLIC_BASE_URL or request.build_absolute_uri("/").rstrip("/")


def _redirect_allowed(uri: str) -> bool:
    parsed = urlparse(uri)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http":
        return host in {"localhost", "127.0.0.1"}
    if parsed.scheme != "https":
        return False
    return any(host == h or host.endswith("." + h) for h in settings.OAUTH_REDIRECT_HOSTS)


def _json_error(error: str, description: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": error, "error_description": description}, status=status)


@require_GET
def authorization_server_metadata(request):
    base = _base_url(request)
    return JsonResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/authorize",
            "token_endpoint": f"{base}/token",
            "registration_endpoint": f"{base}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
            "scopes_supported": ["mcp"],
        }
    )


@require_GET
def protected_resource_metadata(request, resource_path: str = ""):
    base = _base_url(request)
    resource = f"{base}/{resource_path}" if resource_path else base
    return JsonResponse({"resource": resource, "authorization_servers": [base], "scopes_supported": ["mcp"]})


@csrf_exempt
@require_POST
def register(request):
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        return _json_error("invalid_client_metadata", "Body must be JSON.")
    redirect_uris = body.get("redirect_uris") or []
    if not isinstance(redirect_uris, list) or not all(
        isinstance(u, str) and _redirect_allowed(u) for u in redirect_uris
    ):
        return _json_error("invalid_redirect_uri", "Redirect URI not allowed.")
    return JsonResponse(
        {
            **{k: v for k, v in body.items() if isinstance(k, str)},
            "client_id": "learnmcp-" + secrets.token_urlsafe(12),
            "client_id_issued_at": int(time.time()),
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
        status=201,
    )


@require_GET
def authorize(request):
    q = request.GET
    redirect_uri = q.get("redirect_uri", "")
    if not _redirect_allowed(redirect_uri):
        return HttpResponseBadRequest("Redirect URI not allowed.")
    if q.get("response_type") != "code":
        return HttpResponseBadRequest("Only response_type=code is supported.")
    challenge = q.get("code_challenge", "")
    method = q.get("code_challenge_method", "S256" if challenge else "")
    if challenge and method != "S256":
        return HttpResponseBadRequest("Only S256 PKCE is supported.")
    code = signing.dumps(
        {"r": redirect_uri, "c": challenge, "n": secrets.token_urlsafe(8)}, salt=CODE_SALT, compress=True
    )
    params = {"code": code}
    if q.get("state"):
        params["state"] = q["state"]
    sep = "&" if urlparse(redirect_uri).query else "?"
    return HttpResponseRedirect(f"{redirect_uri}{sep}{urlencode(params)}")


def _issue_tokens() -> JsonResponse:
    resp = JsonResponse(
        {
            "access_token": secrets.token_urlsafe(32),
            "token_type": "Bearer",
            "expires_in": TOKEN_LIFETIME,
            "refresh_token": secrets.token_urlsafe(32),
            "scope": "mcp",
        }
    )
    resp["Cache-Control"] = "no-store"
    return resp


@csrf_exempt
@require_POST
def token(request):
    grant = request.POST.get("grant_type")
    if grant == "refresh_token":
        return _issue_tokens()
    if grant != "authorization_code":
        return _json_error("unsupported_grant_type", "Unsupported grant_type.")
    try:
        data = signing.loads(request.POST.get("code", ""), salt=CODE_SALT, max_age=CODE_MAX_AGE)
    except signing.BadSignature:
        return _json_error("invalid_grant", "Invalid or expired code.")
    redirect_uri = request.POST.get("redirect_uri")
    if redirect_uri and redirect_uri != data["r"]:
        return _json_error("invalid_grant", "redirect_uri mismatch.")
    if data["c"]:
        verifier = request.POST.get("code_verifier", "")
        digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        if not secrets.compare_digest(digest, data["c"]):
            return _json_error("invalid_grant", "PKCE verification failed.")
    return _issue_tokens()
