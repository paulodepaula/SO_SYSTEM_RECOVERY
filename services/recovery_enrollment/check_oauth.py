"""Read-only OAuth credential smoke test for the trusted Hermes host.

Run from the repository root as root:
  sudo python3 -m services.recovery_enrollment.check_oauth

The checker authenticates with Tailscale and validates the access-token scope.
It NEVER creates auth keys, joins a device, prints tokens, or needs an ISO.
Only run a reviewed checkout from a trusted, protected directory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://api.tailscale.com/api/v2/oauth/token"
SECRET_DIR = Path("/etc/redeti-recovery")
MAX_SECRET_SIZE = 2048


class CredentialCheckError(Exception):
    """Fixed, non-secret error codes only."""


def load_protected_file(root: Path, filename: str, uid: int = 0) -> str:
    """Enforce root-owned 0700 directory and 0600 regular secret files."""
    if filename not in ("oauth-client-id", "oauth-client-secret"):
        raise CredentialCheckError("invalid_file_name")
    try:
        folder = root.lstat()
        entry = (root / filename).lstat()
    except OSError:
        raise CredentialCheckError("missing_credentials") from None
    if (not stat.S_ISDIR(folder.st_mode) or
        folder.st_uid != uid or stat.S_IMODE(folder.st_mode) != 0o700):
        raise CredentialCheckError("unsafe_secret_directory")
    if (not stat.S_ISREG(entry.st_mode) or
        entry.st_uid != uid or stat.S_IMODE(entry.st_mode) != 0o600 or
        not 1 <= entry.st_size <= MAX_SECRET_SIZE):
        raise CredentialCheckError("unsafe_secret_file")
    try:
        value = (root / filename).read_bytes().decode("ascii").strip()
    except (OSError, UnicodeError):
        raise CredentialCheckError("unreadable_credentials") from None
    if not value or any(ch.isspace() for ch in value):
        raise CredentialCheckError("invalid_credentials")
    return value


def verify_oauth_access(client_id: str, client_secret: str, *,
                        post=None) -> str:
    """Exchange client credentials for a short-lived API token, never mint keys.

    The test transport returns the JSON token response as a dict. The actual
    implementation uses standard certificate/hostname verification.
    """
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "auth_keys",
        "tags": "tag:redeti-recovery",
    }).encode("ascii")
    if post is None:
        post = _post_token
    try:
        response = post(TOKEN_URL, body, {
            "Content-Type": "application/x-www-form-urlencoded",
        })
        if not isinstance(response, dict):
            raise CredentialCheckError("invalid_token_response")
        token = response.get("access_token")
        token_type = response.get("token_type")
        scopes = response.get("scope")
        if not isinstance(token, str) or len(token) < 20:
            raise CredentialCheckError("invalid_token_response")
        if str(token_type).lower() != "bearer":
            raise CredentialCheckError("invalid_token_type")
        if not isinstance(scopes, str) or "auth_keys" not in scopes.split():
            raise CredentialCheckError("invalid_token_scope")
        # Never return/store the OAuth access token.
        return "oauth_auth_keys_valid"
    except CredentialCheckError:
        raise
    except Exception:
        # Provider error bodies can include credential information.
        raise CredentialCheckError("oauth_token_exchange_failed") from None


def _post_token(url: str, body: bytes, headers: dict) -> dict:
    if url != TOKEN_URL:
        raise CredentialCheckError("invalid_destination")
    request = urllib.request.Request(
        url, data=body, headers=headers, method="POST",
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status != 200:
            raise CredentialCheckError("oauth_token_exchange_failed")
        raw = response.read(16385)
    if len(raw) > 16384:
        raise CredentialCheckError("oversized_token_response")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise CredentialCheckError("invalid_token_response")
    return result


def main() -> int:
    if os.geteuid() != 0:
        print("BLOCKED: execute with root privileges for protected files")
        return 2
    try:
        cid = load_protected_file(SECRET_DIR, "oauth-client-id")
        secret = load_protected_file(SECRET_DIR, "oauth-client-secret")
        state = verify_oauth_access(cid, secret)
    except CredentialCheckError as error:
        print("FAIL:", str(error))
        return 1
    print("PASS:", state, "(sem criar auth key nem expor tokens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
