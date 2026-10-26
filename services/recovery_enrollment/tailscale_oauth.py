"""Hermes-side Tailscale OAuth issuer. Never import this module into the ISO.

Only instantiate in the protected broker process after loading OAuth client
credentials from Hermes secret storage. No credentials, real API calls or
customer data are required for the test suite.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Callable, Any

TOKEN_URL = "https://api.tailscale.com/api/v2/oauth/token"
CREATE_KEY_URL = "https://api.tailscale.com/api/v2/tailnet/-/keys"
RECOVERY_TAG = "tag:redeti-recovery"

Transport = Callable[[str, bytes, dict[str, str]], dict[str, Any]]


def _https_json(url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    if url not in (TOKEN_URL, CREATE_KEY_URL):
        raise ValueError("destination not allowlisted")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    # urllib verifies TLS certificates/hostnames by default; never disable.
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status not in (200, 201):
            raise RuntimeError("upstream request failed")
        if int(response.headers.get("Content-Length", "0")) > 16384:
            raise RuntimeError("upstream response too large")
        data = response.read(16385)
    if len(data) > 16384:
        raise RuntimeError("upstream response too large")
    result = json.loads(data)
    if not isinstance(result, dict):
        raise RuntimeError("unexpected upstream response")
    return result


class TailscaleOAuthIssuer:
    """Mints one-off ephemeral keys using OAuth client credentials server-side.

    A real service should load credentials from a local secret manager, not
    accept them through HTTP requests, CLI argv, GitHub or the Recovery USB.
    """

    def __init__(
        self, client_id: str, client_secret: str,
        *, transport: Transport = _https_json
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError("missing OAuth credentials")
        self._id = client_id
        self._secret = client_secret
        self._send = transport

    def __repr__(self) -> str:
        return "TailscaleOAuthIssuer(<credentials-redacted>)"

    def issue_one_off_key(self, *, session_id: str) -> str:
        # Called only after an operator-approved session passes secret proof.
        # Session id is opaque and is not sent in descriptions or logs.
        del session_id
        oauth_data = urllib.parse.urlencode({
            "client_id": self._id, "client_secret": self._secret,
            "grant_type": "client_credentials",
            "scope": "auth_keys",
            "tags": RECOVERY_TAG,
        }).encode("utf-8")
        try:
            token_response = self._send(
                TOKEN_URL, oauth_data,
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
            access_token = token_response["access_token"]
            if not isinstance(access_token, str) or len(access_token) < 20:
                raise RuntimeError("OAuth response invalid")
            request_data = {
                "capabilities": {
                    "devices": {"create": {
                        "reusable": False,
                        "ephemeral": True,
                        "preauthorized": False,
                        "tags": [RECOVERY_TAG],
                    }}
                },
                # Standard Tailscale key expiry is day-based. A one-off key
                # must be consumed during this window; broker TTL is shorter.
                "expirySeconds": 86400,
                "description": "redeti-recovery",
            }
            response = self._send(
                CREATE_KEY_URL, json.dumps(request_data).encode("utf-8"),
                {"Authorization": "Bearer " + access_token,
                 "Content-Type": "application/json"},
            )
            key = response["key"]
            if not isinstance(key, str) or not key.startswith("tskey-auth-"):
                raise RuntimeError("auth key response invalid")
            # The API returns capabilities. If missing or conflicting, do not
            # deliver an auth key whose scope we cannot verify.
            created = response["capabilities"]["devices"]["create"]
            if (created.get("reusable") is not False or
                created.get("ephemeral") is not True or
                created.get("tags") != [RECOVERY_TAG] or
                created.get("preauthorized") is not False):
                raise RuntimeError("unsafe key capabilities")
            return key
        except Exception:
            # Upstream error bodies could contain credentials: never forward
            # provider exceptions into logs, dashboards or HTTP responses.
            raise RuntimeError("Tailscale enrollment unavailable") from None
