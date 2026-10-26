"""In-memory authorization core for the future Hermes enrollment broker.

Important: This module is NOT an HTTP server. Only a separate, authenticated
operator endpoint may invoke approve(). All exchanges must use HTTPS. No
OAuth/admin credentials, tokens or customer data should appear in logs.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac
import secrets
import threading
import time
from typing import Callable, Protocol


class EnrollmentError(Exception):
    """A deliberately generic error; never embeds credential contents."""


class EnrollmentState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ISSUING = "issuing"
    CONSUMED = "consumed"
    FAILED = "failed"
    EXPIRED = "expired"


class KeyIssuer(Protocol):
    def issue_one_off_key(self, *, session_id: str) -> str:
        """Return one single-use ephemeral tagged auth key (never log it)."""


@dataclass(frozen=True)
class RequestReceipt:
    session_id: str
    pairing_code: str
    agent_secret: str
    expires_at: float


@dataclass
class _Entry:
    session_id: str
    secret_digest: bytes
    code_digest: bytes
    source: str
    created_at: float
    expires_at: float
    state: EnrollmentState = EnrollmentState.PENDING
    approved_by: str | None = None
    work_order: str | None = None


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("ascii")).digest()


class EnrollmentBroker:
    """Fail-closed, zero-disk state machine; *not* a deployed API service.

    Generate claim secret server-side and transmit once via authenticated TLS.
    Approval must be called ONLY by a separately authenticated operator route.
    A short visual pairing code is NOT an authentication credential.
    """

    def __init__(
        self,
        issuer: KeyIssuer,
        *,
        clock: Callable[[], float] = time.time,
        approval_ttl_seconds: int = 180,
        rate_limit_window_seconds: int = 600,
        max_requests_per_source: int = 6,
        max_sessions: int = 256,
        audit: Callable[[str, str], None] | None = None,
    ) -> None:
        if not 30 <= approval_ttl_seconds <= 600:
            raise ValueError("approval TTL must be between 30 and 600 seconds")
        if max_requests_per_source < 1 or max_sessions < 1:
            raise ValueError("limits must be positive")
        self._issuer = issuer
        self._clock = clock
        self._ttl = approval_ttl_seconds
        self._window = rate_limit_window_seconds
        self._per_source = max_requests_per_source
        self._max_sessions = max_sessions
        self._entries: dict[str, _Entry] = {}
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()
        self._audit = audit

    def _event(self, name: str, session_id: str) -> None:
        # Events contain a random opaque id only; never keys, codes or secrets.
        if self._audit is not None:
            try:
                self._audit(name, session_id)
            except Exception:
                # An audit transport must not leak secrets or mint extra keys.
                pass

    def _expire(self, entry: _Entry, now: float) -> None:
        if now >= entry.expires_at and entry.state in (
            EnrollmentState.PENDING, EnrollmentState.APPROVED
        ):
            entry.state = EnrollmentState.EXPIRED
            self._event("expired", entry.session_id)

    def request(self, *, source: str) -> RequestReceipt:
        """Register an untrusted device. Source comes from trusted HTTP peer."""
        if not source or len(source) > 128:
            raise EnrollmentError("invalid request")
        with self._lock:
            now = self._clock()
            attempts = self._attempts[source]
            while attempts and attempts[0] <= now - self._window:
                attempts.popleft()
            if len(attempts) >= self._per_source:
                raise EnrollmentError("rate limit exceeded")
            # Resource cap is explicit; persistent storage is not used.
            for sid, entry in list(self._entries.items()):
                self._expire(entry, now)
                if entry.state in (EnrollmentState.EXPIRED,
                                   EnrollmentState.CONSUMED, EnrollmentState.FAILED):
                    del self._entries[sid]
            if len(self._entries) >= self._max_sessions:
                raise EnrollmentError("enrollment capacity reached")
            attempts.append(now)
            sid = secrets.token_urlsafe(24)
            code = f"{secrets.randbelow(100_000_000):08d}"
            secret = secrets.token_urlsafe(32)
            self._entries[sid] = _Entry(
                session_id=sid,
                secret_digest=_digest(sid + ":" + secret),
                code_digest=_digest(sid + ":" + code),
                source=source,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._event("requested", sid)
            return RequestReceipt(sid, code, secret, now + self._ttl)

    def state(self, session_id: str) -> str:
        """State is non-secret. It does not indicate if a key is available."""
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return "unknown"
            self._expire(entry, self._clock())
            return entry.state.value

    def approve(
        self, *, session_id: str, pairing_code: str,
        operator_id: str, work_order: str
    ) -> None:
        """ONLY a trusted, authenticated operator endpoint may call this.

        Identity and work-order authorization MUST be established before this
        function; do not allow direct public HTTP access to approve().
        """
        if not operator_id or not work_order or len(operator_id) > 128 or len(work_order) > 128:
            raise EnrollmentError("authorization required")
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                raise EnrollmentError("session unavailable")
            self._expire(entry, self._clock())
            if entry.state != EnrollmentState.PENDING:
                raise EnrollmentError("session unavailable")
            # Fixed-length code, constant-time digest comparison.
            valid_shape = len(pairing_code) == 8 and pairing_code.isascii() and pairing_code.isdigit()
            candidate = _digest(session_id + ":" + pairing_code) if valid_shape else bytes(32)
            if not hmac.compare_digest(candidate, entry.code_digest):
                self._event("rejected_approval", session_id)
                raise EnrollmentError("pairing code mismatch")
            entry.approved_by = operator_id
            entry.work_order = work_order
            entry.state = EnrollmentState.APPROVED
            self._event("approved", session_id)

    def claim(self, *, session_id: str, agent_secret: str) -> str:
        """Deliver token ONCE to the original agent over HTTPS.

        On an issuer/network error the session fails closed and requires a new
        request. Issued keys are never cached, printed or returned on retry.
        """
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                raise EnrollmentError("session unavailable")
            self._expire(entry, self._clock())
            if entry.state != EnrollmentState.APPROVED:
                raise EnrollmentError("session unavailable")
            if not isinstance(agent_secret, str) or len(agent_secret) > 128:
                raise EnrollmentError("session unavailable")
            candidate = _digest(session_id + ":" + agent_secret)
            if not hmac.compare_digest(candidate, entry.secret_digest):
                self._event("rejected_claim", session_id)
                raise EnrollmentError("session unavailable")
            entry.state = EnrollmentState.ISSUING
        try:
            # No lock while making a potentially slow external API call. State
            # ISSUING prevents concurrent issuance/replay.
            key = self._issuer.issue_one_off_key(session_id=session_id)
            if not isinstance(key, str) or not key.startswith("tskey-auth-"):
                raise EnrollmentError("issuer rejected request")
        except Exception:
            with self._lock:
                entry.state = EnrollmentState.FAILED
                self._event("failed", session_id)
            raise EnrollmentError("enrollment failed") from None
        with self._lock:
            entry.state = EnrollmentState.CONSUMED
            self._event("consumed", session_id)
        return key
