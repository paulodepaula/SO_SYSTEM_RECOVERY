"""Explicit, one-off REAL API test for an OAuth-created Tailscale auth key.

Run ONLY on the trusted Hermes host and ONLY when the operator intentionally
chooses to exercise the live Tailscale API:

    sudo python3 -m services.recovery_enrollment.check_authkey_lifecycle --create-and-revoke

This creates one single-use, ephemeral, NOT preauthorized key valid for
900 seconds, checks its returned metadata, and immediately REVOKES it.
No agent/device joins the tailnet. The key, OAuth access token and client
secret NEVER appear on stdout, logs, argv, or in a file.

This smoke test is distinct from the production issuer, which may set
preauthorized=True ONLY after a technician-approved broker session.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from .check_oauth import SECRET_DIR, load_protected_file
from .tailscale_oauth import CREATE_KEY_URL, RECOVERY_TAG, TOKEN_URL

KEY_ID = re.compile(r"^[A-Za-z0-9_-]{4,128}$")
MAX_RESPONSE = 16384

Transport = Callable[[str, str, bytes | None, dict[str, str]], dict]


class LifecycleCheckError(Exception):
    """Fixed, nonsecret state code only."""


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LifecycleCheckError("redirect_blocked")


def _transport(method: str, url: str, body: bytes | None,
               headers: dict[str, str]) -> dict:
    if (method, url) not in (
        ("POST", TOKEN_URL), ("POST", CREATE_KEY_URL)
    ) and not (method == "DELETE" and url.startswith(CREATE_KEY_URL + "/")
               and KEY_ID.fullmatch(url.removeprefix(CREATE_KEY_URL + "/"))):
        raise LifecycleCheckError("destination_blocked")
    opener = urllib.request.build_opener(_NoRedirects())
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(request, timeout=12) as response:
            if response.status not in (200, 201, 204):
                raise LifecycleCheckError("api_request_failed")
            data = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as error:
        # Only the numeric HTTP status is safe to expose. Provider bodies,
        # exception strings and credentials must never appear in logs.
        raise LifecycleCheckError(f"api_http_{error.code}") from None
    except LifecycleCheckError:
        raise
    except Exception:
        raise LifecycleCheckError("api_transport_unavailable") from None
    if len(data) > MAX_RESPONSE:
        raise LifecycleCheckError("oversized_api_response")
    if not data:
        return {}
    value = json.loads(data)
    if not isinstance(value, dict):
        raise LifecycleCheckError("invalid_api_response")
    return value


def _valid_capabilities(result: dict) -> bool:
    try:
        c = result["capabilities"]["devices"]["create"]
        return (
            isinstance(result.get("key"), str)
            and result["key"].startswith("tskey-auth-")
            and c.get("reusable") is False
            and c.get("ephemeral") is True
            and c.get("preauthorized") is False
            and c.get("tags") == [RECOVERY_TAG]
        )
    except (KeyError, TypeError, AttributeError):
        return False


def check_lifecycle(client_id: str, client_secret: str,
                    *, transport: Transport = _transport) -> str:
    """Create exactly one disposable key, verify, revoke; never return it."""
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "auth_keys",
        "tags": RECOVERY_TAG,
    }).encode("ascii")
    access_token = None
    try:
        token = transport("POST", TOKEN_URL, payload,
                          {"Content-Type": "application/x-www-form-urlencoded"})
        access_token = token["access_token"]
        if (not isinstance(access_token, str) or len(access_token) < 20
            or str(token.get("token_type")).lower() != "bearer"
            or "auth_keys" not in str(token.get("scope", "")).split()):
            raise LifecycleCheckError("oauth_scope_unavailable")
    except LifecycleCheckError:
        raise
    except Exception:
        raise LifecycleCheckError("oauth_exchange_failed") from None

    headers = {"Authorization": "Bearer " + access_token,
               "Content-Type": "application/json"}
    spec = {
        "capabilities": {"devices": {"create": {
            "reusable": False, "ephemeral": True, "preauthorized": False,
            "tags": [RECOVERY_TAG]
        }}},
        "expirySeconds": 900,
        "description": "redeti-recovery-smoke",
    }
    key_id = None
    revoke_verified = False
    # A failed HTTP request may have created a key before the response was
    # lost. Do not automatically retry creating another key.
    try:
        result = transport("POST", CREATE_KEY_URL,
                           json.dumps(spec).encode("ascii"), headers)
        key_id = result.get("id")
        if not isinstance(key_id, str) or not KEY_ID.fullmatch(key_id):
            raise LifecycleCheckError("creation_unknown_review_keys_panel")
        if not _valid_capabilities(result):
            raise LifecycleCheckError("created_key_capabilities_invalid")
    except LifecycleCheckError:
        raise
    except Exception:
        raise LifecycleCheckError("creation_unknown_review_keys_panel") from None
    finally:
        if key_id is not None and isinstance(key_id, str) and KEY_ID.fullmatch(key_id):
            # Revoke even when the returned key's capabilities are unexpected.
            try:
                transport("DELETE", CREATE_KEY_URL + "/" + key_id, None,
                          {"Authorization": "Bearer " + access_token})
                revoke_verified = True
            except LifecycleCheckError as error:
                # Report only a sanitized HTTP status (e.g. 403/404).
                # It is diagnostic, not proof that the key stayed active.
                code = str(error)
                if re.fullmatch(r"api_http_[1-5][0-9][0-9]", code):
                    raise LifecycleCheckError(
                        "revocation_" + code + "_review_keys_panel"
                    ) from None
                raise LifecycleCheckError(
                    "revocation_unverified_review_keys_panel"
                ) from None
            except Exception:
                raise LifecycleCheckError(
                    "revocation_unverified_review_keys_panel"
                ) from None
    return "real_authkey_created_and_revoked"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--create-and-revoke"]:
        print("BLOCKED: explicit --create-and-revoke required")
        return 2
    if os.geteuid() != 0:
        print("BLOCKED: use sudo to access root-owned credentials")
        return 2
    try:
        client_id = load_protected_file(SECRET_DIR, "oauth-client-id")
        client_secret = load_protected_file(SECRET_DIR, "oauth-client-secret")
        result = check_lifecycle(client_id, client_secret)
    except LifecycleCheckError as error:
        print("FAIL:", str(error))
        return 1
    except Exception:
        print("FAIL: credentials_or_runtime_unavailable")
        return 1
    print("PASS:", result, "(chave descartavel revogada; nenhum token exibido)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
