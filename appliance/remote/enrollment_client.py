#!/usr/bin/env python3
"""Fail-closed Recovery Agent enrollment client.

This module contains the client-side state machine only. It never contains
OAuth credentials and never persists an enrollment key. Production transport
must be HTTPS and injected/configured outside the ISO; tests use a fake
transport and never contact Hermes or Tailscale.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping
import urllib.error
import urllib.parse
import urllib.request


class EnrollmentClientError(Exception):
    """Generic client failure; never contains a secret or provider response."""


class VpnState(str, Enum):
    SEM_REDE = "SEM_REDE"
    AGUARDANDO_AUTORIZACAO = "AGUARDANDO_AUTORIZACAO"
    AUTORIZADO = "AUTORIZADO"
    CONECTANDO = "CONECTANDO"
    CONECTADO = "CONECTADO"
    FALHA = "FALHA"
    SESSAO_ENCERRADA = "SESSAO_ENCERRADA"


@dataclass(frozen=True)
class EnrollmentStatus:
    state: VpnState
    pairing_code: str = ""
    expires_at: float = 0.0
    reason: str = ""

    def public_json(self) -> dict[str, Any]:
        """Return UI-safe state; never include agent secret or auth key."""
        return {
            "state": self.state.value,
            "pairing_code": self.pairing_code if self.state == VpnState.AGUARDANDO_AUTORIZACAO else "",
            "expires_at": self.expires_at if self.state == VpnState.AGUARDANDO_AUTORIZACAO else 0,
            "reason": self.reason,
        }


Transport = Callable[[str, str, Mapping[str, str], bytes], Mapping[str, Any]]


_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{24,80}$")
_CODE = re.compile(r"^[0-9]{8}$")
_SECRET = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_KEY = re.compile(r"^tskey-auth-[A-Za-z0-9_-]{10,240}$")


def _https_transport(method: str, url: str, headers: Mapping[str, str], body: bytes) -> Mapping[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise EnrollmentClientError("invalid enrollment endpoint")
    request = urllib.request.Request(url, data=body or None, headers=dict(headers), method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = response.read(16385)
            if len(data) > 16384 or response.status not in (200, 201):
                raise EnrollmentClientError("enrollment unavailable")
    except (OSError, urllib.error.URLError, TimeoutError):
        raise EnrollmentClientError("enrollment unavailable") from None
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise EnrollmentClientError("invalid enrollment response") from None
    if not isinstance(value, dict):
        raise EnrollmentClientError("invalid enrollment response")
    return value


class EnrollmentClient:
    """Short-lived enrollment state machine with memory-only credentials."""

    def __init__(
        self,
        endpoint: str,
        *,
        transport: Transport = _https_transport,
        clock: Callable[[], float] = time.time,
        max_polls: int = 60,
    ) -> None:
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("enrollment endpoint must be HTTPS without query or credentials")
        if not parsed.netloc or not endpoint.rstrip("/").endswith("/v1/bootstrap"):
            raise ValueError("invalid enrollment endpoint")
        if not 1 <= max_polls <= 600:
            raise ValueError("invalid poll limit")
        self._endpoint = endpoint.rstrip("/")
        self._transport = transport
        self._clock = clock
        self._max_polls = max_polls
        self._polls = 0
        self._session_id = ""
        self._agent_secret = ""
        self._auth_key = ""
        self._status = EnrollmentStatus(VpnState.SEM_REDE)

    @property
    def status(self) -> EnrollmentStatus:
        return self._status

    def start(self, *, network_available: bool) -> EnrollmentStatus:
        if not network_available:
            return self._set(VpnState.SEM_REDE, "network_unavailable")
        try:
            response = self._transport(
                "POST", self._endpoint + "/sessions",
                {"Content-Type": "application/json", "Cache-Control": "no-store"}, b"",
            )
            sid = response.get("session_id")
            code = response.get("pairing_code")
            secret = response.get("agent_secret")
            expires = response.get("expires_at")
            if (not isinstance(sid, str) or not _SESSION_ID.fullmatch(sid)
                    or not isinstance(code, str) or not _CODE.fullmatch(code)
                    or not isinstance(secret, str) or not _SECRET.fullmatch(secret)
                    or not isinstance(expires, (int, float))):
                raise EnrollmentClientError("invalid enrollment response")
            if expires <= self._clock():
                raise EnrollmentClientError("enrollment expired")
            self._session_id, self._agent_secret = sid, secret
            self._polls = 0
            return self._set(VpnState.AGUARDANDO_AUTORIZACAO, "", code, float(expires))
        except EnrollmentClientError:
            return self._fail("bootstrap_failed")
        except Exception:
            return self._fail("bootstrap_failed")

    def poll(self) -> EnrollmentStatus:
        if self._status.state != VpnState.AGUARDANDO_AUTORIZACAO:
            return self._status
        if self._clock() >= self._status.expires_at or self._polls >= self._max_polls:
            return self._fail("authorization_expired")
        self._polls += 1
        try:
            response = self._transport(
                "GET", self._endpoint + "/sessions/" + self._session_id,
                {"Authorization": "Bearer " + self._agent_secret,
                 "Cache-Control": "no-store"}, b"",
            )
            state = response.get("state")
            if state == "pending":
                return self._status
            if state == "approved":
                return self._set(VpnState.AUTORIZADO)
            if state in {"expired", "failed", "consumed"}:
                return self._fail("broker_" + state)
            return self._fail("invalid_broker_state")
        except Exception:
            return self._fail("broker_unavailable")

    def claim_auth_key(self) -> str:
        if self._status.state != VpnState.AUTORIZADO:
            raise EnrollmentClientError("authorization required")
        try:
            response = self._transport(
                "POST", self._endpoint + "/sessions/" + self._session_id + "/claim",
                {"Authorization": "Bearer " + self._agent_secret,
                 "Cache-Control": "no-store"}, b"",
            )
            key = response.get("auth_key")
            if not isinstance(key, str) or not _KEY.fullmatch(key):
                raise EnrollmentClientError("invalid enrollment key")
            self._auth_key = key
            self._agent_secret = ""
            self._set(VpnState.CONECTANDO)
            return key
        except Exception:
            self._agent_secret = ""
            self._auth_key = ""
            self._set(VpnState.FALHA, "claim_failed")
            raise EnrollmentClientError("claim failed") from None

    def consume_auth_key(self) -> str:
        """Return the key once and erase the client copy immediately."""
        if not self._auth_key:
            raise EnrollmentClientError("enrollment key unavailable")
        key, self._auth_key = self._auth_key, ""
        return key

    def connected(self) -> EnrollmentStatus:
        if self._status.state != VpnState.CONECTANDO:
            raise EnrollmentClientError("connection not pending")
        return self._set(VpnState.CONECTADO)

    def close(self, *, reason: str = "operator_cancelled") -> EnrollmentStatus:
        self._clear_private()
        return self._set(VpnState.SESSAO_ENCERRADA, reason)

    def _fail(self, reason: str) -> EnrollmentStatus:
        self._clear_private()
        return self._set(VpnState.FALHA, reason)

    def _clear_private(self) -> None:
        self._session_id = ""
        self._agent_secret = ""
        self._auth_key = ""

    def _set(
        self, state: VpnState, reason: str = "", pairing_code: str = "", expires_at: float = 0.0
    ) -> EnrollmentStatus:
        self._status = EnrollmentStatus(state, pairing_code, expires_at, reason)
        return self._status


def write_status(path: str | Path, status: EnrollmentStatus) -> None:
    """Atomically write only UI-safe state to a RAM-backed status path."""
    target = Path(path)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(status.public_json(), separators=(",", ":")) + "\n")
    temporary.chmod(0o644)
    temporary.replace(target)


if __name__ == "__main__":
    raise SystemExit("client library only; production transport is not configured")
