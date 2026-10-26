"""Verified Service Desk approval assertions; server-only, not part of ISO.

A protected Service Desk backend MAY sign a short-lived operator assertion
after checking its *actual session*, MFA, permission, and ownership of the OS.
The Hermes broker verifies signature, audience, expiry and unique nonce before
approving the existing pairing state.

This is NOT a public authentication mechanism. A claim that merely says
'role=ADMIN' without a valid MAC must never be accepted.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from typing import Callable

from .core import EnrollmentBroker, EnrollmentError

_AUDIENCE = "redeti-recovery-enrollment"
_ISSUER = "redeti-servicedesk"
_PERMISSION = "RECOVERY_VPN_APPROVE"
_ALLOWED_ROLES = frozenset({"SUPER_ADMIN", "ADMIN", "GESTOR"})
_FIELDS = frozenset({
    "version", "aud", "iss", "sid", "code", "operator", "role",
    "permission", "os_id", "iat", "exp", "nonce",
})
_B64 = re.compile(r"^[A-Za-z0-9_-]+$")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_NONCE = re.compile(r"^[A-Za-z0-9_-]{24,80}$")


class OperatorAuthError(EnrollmentError):
    """Generic verification failure; no signed payload or secret in message."""


def _encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    if not value or not _B64.fullmatch(value) or len(value) > 4096:
        raise OperatorAuthError("operator authorization denied")
    try:
        data = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error):
        raise OperatorAuthError("operator authorization denied") from None
    if _encode(data) != value:
        raise OperatorAuthError("operator authorization denied")
    return data


class OperatorApprovalVerifier:
    """Validate signed approvals; MAC key comes only from a Hermes secret store.

    Tests use a fake signing utility. Production signing must occur only in
    the authenticated Service Desk API after DB-backed permission/OS checks.
    """

    def __init__(
        self, broker: EnrollmentBroker, *, mac_secret: bytes,
        clock: Callable[[], float] = time.time, max_nonces: int = 4096
    ) -> None:
        if not isinstance(mac_secret, bytes) or len(mac_secret) < 32:
            raise ValueError("operator signing key must be at least 32 bytes")
        if max_nonces < 1:
            raise ValueError("invalid replay protection capacity")
        self._secret = mac_secret
        self._broker = broker
        self._clock = clock
        self._max_nonces = max_nonces
        self._used: dict[str, int] = {}
        self._lock = threading.RLock()

    def approve_signed(
        self, assertion: str, *, expected_session_id: str | None = None
    ) -> None:
        """One use only, no logs and no authorization based on unsigned JSON."""
        fail = OperatorAuthError("operator authorization denied")
        if not isinstance(assertion, str) or len(assertion) > 6000:
            raise fail
        parts = assertion.split(".")
        if len(parts) != 3 or parts[0] != "v1":
            raise fail
        body = _decode(parts[1])
        signature = _decode(parts[2])
        if len(signature) != hashlib.sha256().digest_size:
            raise fail
        signed = ("v1." + parts[1]).encode("ascii")
        mac = hmac.new(self._secret, signed, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, mac):
            raise fail
        if len(body) > 2048:
            raise fail
        try:
            data = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise fail from None
        if not isinstance(data, dict) or set(data) != _FIELDS:
            raise fail
        now = int(self._clock())
        if (type(data["version"]) is not int or data["version"] != 1
            or data["aud"] != _AUDIENCE or data["iss"] != _ISSUER
            or data["permission"] != _PERMISSION
            or not isinstance(data["role"], str)
            or data["role"] not in _ALLOWED_ROLES
            or type(data["iat"]) is not int or type(data["exp"]) is not int
            or data["iat"] > now + 10 or data["iat"] < now - 120
            or data["exp"] <= now or data["exp"] > data["iat"] + 120
            or not isinstance(data["sid"], str)
            or not _ID.fullmatch(data["sid"]) or len(data["sid"]) < 24
            or not isinstance(data["code"], str)
            or len(data["code"]) != 8 or not data["code"].isascii()
            or not data["code"].isdigit()
            or not isinstance(data["operator"], str)
            or not _ID.fullmatch(data["operator"])
            or not isinstance(data["os_id"], str)
            or not _ID.fullmatch(data["os_id"])
            or not isinstance(data["nonce"], str)
            or not _NONCE.fullmatch(data["nonce"])):
            raise fail

        if expected_session_id is not None and not hmac.compare_digest(
            data["sid"], expected_session_id
        ):
            raise fail

        with self._lock:
            # Fixed resource bound and fail-closed replay check. In a scaled
            # deployment replace with an atomic shared nonce store.
            for nonce, expiry in list(self._used.items()):
                if expiry <= now:
                    del self._used[nonce]
            if data["nonce"] in self._used or len(self._used) >= self._max_nonces:
                raise fail
            # Record before approval even if the pairing code is invalid.
            # A signed assertion cannot be reused for guessing.
            self._used[data["nonce"]] = data["exp"]
            try:
                self._broker.approve(
                    session_id=data["sid"], pairing_code=data["code"],
                    operator_id=data["operator"], work_order=data["os_id"],
                )
            except EnrollmentError:
                raise fail from None


def sign_example_for_tests(
    payload: dict[str, object], *, mac_secret: bytes
) -> str:
    """Offline testing only. Never expose this signer in an agent HTTP route."""
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    part = "v1." + _encode(data)
    mac = hmac.new(mac_secret, part.encode("ascii"), hashlib.sha256).digest()
    return part + "." + _encode(mac)


def example_claim_for_tests(
    *, sid: str, code: str, now: int, operator: str = "tech123",
    role: str = "GESTOR", os_id: str = "OS_42",
) -> dict[str, object]:
    """Safe test-only generator, deliberately includes no real customer data."""
    return {
        "version": 1, "aud": _AUDIENCE, "iss": _ISSUER,
        "sid": sid, "code": code,
        "operator": operator, "role": role, "os_id": os_id,
        "permission": _PERMISSION, "iat": now, "exp": now + 60,
        "nonce": secrets.token_urlsafe(24),
    }
