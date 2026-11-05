import base64
import hashlib
import json
from urllib.parse import parse_qs, urlparse

CALLBACK = "https://claude.ai/api/mcp/auth_callback"


def test_discovery_metadata(client, settings):
    settings.PUBLIC_BASE_URL = "https://learn.example.com"
    meta = client.get("/.well-known/oauth-authorization-server").json()
    assert meta["registration_endpoint"] == "https://learn.example.com/register"
    assert meta["authorization_endpoint"] == "https://learn.example.com/authorize"
    assert "S256" in meta["code_challenge_methods_supported"]

    prm = client.get("/.well-known/oauth-protected-resource/s/abc/mcp").json()
    assert prm["resource"] == "https://learn.example.com/s/abc/mcp"
    assert prm["authorization_servers"] == ["https://learn.example.com"]


def test_register_rejects_foreign_redirect(client):
    resp = client.post(
        "/register", json.dumps({"redirect_uris": ["https://evil.example/cb"]}), content_type="application/json"
    )
    assert resp.status_code == 400


def test_full_flow_with_pkce(client):
    reg = client.post(
        "/register",
        json.dumps({"client_name": "Claude", "redirect_uris": [CALLBACK]}),
        content_type="application/json",
    )
    assert reg.status_code == 201
    client_id = reg.json()["client_id"]

    verifier = "v" * 50
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    resp = client.get(
        "/authorize",
        {"response_type": "code", "client_id": client_id, "redirect_uri": CALLBACK, "state": "xyz",
         "code_challenge": challenge, "code_challenge_method": "S256"},
    )
    assert resp.status_code == 302
    loc = urlparse(resp.url)
    assert f"{loc.scheme}://{loc.netloc}{loc.path}" == CALLBACK
    params = parse_qs(loc.query)
    assert params["state"] == ["xyz"]
    code = params["code"][0]

    bad = client.post("/token", {"grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK,
                                 "code_verifier": "wrong"})
    assert bad.status_code == 400

    tok = client.post("/token", {"grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK,
                                 "client_id": client_id, "code_verifier": verifier})
    assert tok.status_code == 200
    body = tok.json()
    assert body["token_type"] == "Bearer" and body["access_token"] and body["refresh_token"]

    ref = client.post("/token", {"grant_type": "refresh_token", "refresh_token": body["refresh_token"]})
    assert ref.status_code == 200


def test_authorize_rejects_foreign_redirect(client):
    resp = client.get("/authorize", {"response_type": "code", "redirect_uri": "https://evil.example/cb"})
    assert resp.status_code == 400


def test_token_rejects_garbage_code(client):
    resp = client.post("/token", {"grant_type": "authorization_code", "code": "nope"})
    assert resp.status_code == 400 and resp.json()["error"] == "invalid_grant"
