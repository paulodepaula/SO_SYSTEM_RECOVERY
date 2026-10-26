"""Read-only inventory of OAuth-issued REDETI smoke auth keys.

Run only on trusted Hermes:
    sudo python3 -m services.recovery_enrollment.inspect_smoke_keys

No new keys, no revocations, no device actions, no printed IDs or tokens.
This is a reconciliation diagnostic AFTER a failed create-and-revoke test.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Callable, Any

from .check_oauth import SECRET_DIR, load_protected_file
from .tailscale_oauth import TOKEN_URL, CREATE_KEY_URL, RECOVERY_TAG

_SMOKE_NAME = "redeti-recovery-smoke"
_KEY_ID = re.compile(r"^[A-Za-z0-9_-]{4,128}$")


class InventoryError(Exception):
    """Fixed, non-secret diagnostic message."""


def _get_json(method: str, url: str, data: bytes | None,
              headers: dict[str, str]) -> dict[str, Any]:
    if method == "POST" and url == TOKEN_URL:
        pass
    elif method == "GET" and (url == CREATE_KEY_URL or (
            url.startswith(CREATE_KEY_URL + "/") and
            _KEY_ID.fullmatch(url[len(CREATE_KEY_URL) + 1:]))):
        pass
    else:
        raise InventoryError("destination_denied")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hs, newurl):
            raise InventoryError("redirect_denied")
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=12) as response:
            if response.status != 200:
                raise InventoryError("unexpected_api_status")
            body = response.read(16385)
    except urllib.error.HTTPError as exc:
        raise InventoryError(f"api_http_{exc.code}") from None
    except InventoryError:
        raise
    except Exception:
        raise InventoryError("api_unavailable") from None
    if len(body) > 16384:
        raise InventoryError("api_response_too_large")
    try:
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, UnicodeError):
        raise InventoryError("invalid_api_response") from None


def _is_active(item: dict[str, Any], now: datetime) -> bool:
    if item.get("invalid") is True or item.get("revoked"):
        return False
    expires = item.get("expires")
    if not isinstance(expires, str):
        return False  # Indeterminate metadata is never declared safe.
    try:
        when = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if when.tzinfo is None:
            return False
        return when > now
    except ValueError:
        return False


def inventory_smoke_keys(
    client_id: str, client_secret: str, *,
    transport: Callable[[str, str, bytes | None, dict[str, str]], dict[str, Any]] = _get_json,
    now: datetime | None = None,
) -> tuple[int, int, int]:
    """Return (active, inactive, uncertain) counts, without exposing IDs."""
    body = urllib.parse.urlencode({
        "client_id": client_id, "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "auth_keys",
        "tags": RECOVERY_TAG,
    }).encode("ascii")
    try:
        token_data = transport("POST", TOKEN_URL, body,
                               {"Content-Type": "application/x-www-form-urlencoded"})
        access_token = token_data["access_token"]
        if (not isinstance(access_token, str) or len(access_token) < 20
            or str(token_data.get("token_type", "")).lower() != "bearer"
            or "auth_keys" not in str(token_data.get("scope", "")).split()):
            raise InventoryError("oauth_scope_unavailable")
        headers = {"Authorization": "Bearer " + access_token}
        listing = transport("GET", CREATE_KEY_URL, None, headers)
        ids = listing["keys"]
        if not isinstance(ids, list) or len(ids) > 500:
            raise InventoryError("unexpected_key_listing")
        active = inactive = uncertain = 0
        current = now or datetime.now(timezone.utc)
        for entry in ids:
            key_id = entry.get("id") if isinstance(entry, dict) else None
            if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
                raise InventoryError("unexpected_key_id")
            try:
                detail = transport("GET", CREATE_KEY_URL + "/" + key_id,
                                   None, headers)
            except InventoryError as e:
                if str(e) == "api_http_404":
                    continue  # Raced with expiration/revocation.
                raise
            if detail.get("description") != _SMOKE_NAME:
                continue
            caps = detail.get("capabilities", {}).get("devices", {}).get("create", {})
            if not isinstance(caps, dict) or caps.get("tags") != [RECOVERY_TAG]:
                continue
            if _is_active(detail, current):
                active += 1
            elif detail.get("invalid") is True or detail.get("revoked"):
                inactive += 1
            else:
                uncertain += 1
        return active, inactive, uncertain
    except InventoryError:
        raise
    except Exception:
        raise InventoryError("inventory_unavailable") from None


def main() -> int:
    if os.geteuid() != 0:
        print("BLOCKED: sudo required")
        return 2
    try:
        cid = load_protected_file(SECRET_DIR, "oauth-client-id")
        sec = load_protected_file(SECRET_DIR, "oauth-client-secret")
        a, i, u = inventory_smoke_keys(cid, sec)
    except InventoryError as ex:
        print("FAIL:", str(ex))
        return 1
    except Exception:
        print("FAIL: credentials_unavailable")
        return 1
    print(f"SMOKE_ACTIVE={a} SMOKE_INACTIVE={i} SMOKE_UNCERTAIN={u}")
    if a or u:
        print("ACTION: verify/revoke redeti-recovery-smoke in Tailscale Keys")
    else:
        print("PASS: no active smoke keys visible to this OAuth credential")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
