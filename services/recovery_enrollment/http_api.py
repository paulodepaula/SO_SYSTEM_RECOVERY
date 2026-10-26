"""Private, loopback-only HTTP adapter for the Hermes enrollment core.

NOT a public Internet listener and NOT a deployed field service.
Operator approval is intentionally NOT an HTTP endpoint here: integrate the
Service Desk authenticated/authorized operator route separately. An HTTPS
reverse proxy may eventually forward only the bootstrap routes, after rate
limiting, TLS configuration and audit review.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from typing import Any

from .core import EnrollmentBroker, EnrollmentError

_PREFIX = "/v1/bootstrap/sessions"
_SESSION = re.compile(r"^/v1/bootstrap/sessions/([A-Za-z0-9_-]{24,80})$")
_CLAIM = re.compile(r"^/v1/bootstrap/sessions/([A-Za-z0-9_-]{24,80})/claim$")
_MAX_BODY = 256


def _handler(broker: EnrollmentBroker) -> type[BaseHTTPRequestHandler]:
    """Per-server handler class; never place secrets into module globals."""
    class Handler(BaseHTTPRequestHandler):
        server_version = "RecoveryBroker"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: object) -> None:
            # Deliberately no URL, agent secret, authentication or response
            # logging. A separate trusted audit sink receives state events.
            pass

        def _reply(self, status: int, payload: dict[str, Any] | None = None) -> None:
            body = json.dumps(payload or {}, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, private")
            self.send_header("Pragma", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def _empty_body(self) -> bool:
            # Reject request smuggling and unexpected content. Session and
            # claim endpoints deliberately have no request body.
            if self.headers.get("Transfer-Encoding") is not None:
                return False
            length = self.headers.get("Content-Length", "0")
            return length.isascii() and length.isdigit() and int(length) == 0

        def _agent_secret(self) -> str | None:
            # Agent proofs must never be transmitted in URL/query string.
            authorization = self.headers.get("Authorization", "")
            if not authorization.startswith("Bearer "):
                return None
            value = authorization[7:]
            if (not 32 <= len(value) <= 128 or
                    not re.fullmatch(r"[A-Za-z0-9_-]+", value)):
                return None
            return value

        def do_POST(self) -> None:
            if "?" in self.path or not self._empty_body():
                self._reply(400, {"error": "invalid request"})
                return
            if self.path == _PREFIX:
                try:
                    # Source is from the actual loopback peer, not untrusted
                    # X-Forwarded-For. Ingress must impose its own IP limits.
                    receipt = broker.request(source=self.client_address[0])
                except EnrollmentError:
                    self._reply(429, {"error": "request unavailable"})
                    return
                self._reply(201, {
                    "session_id": receipt.session_id,
                    "pairing_code": receipt.pairing_code,
                    "agent_secret": receipt.agent_secret,
                    "expires_at": receipt.expires_at,
                })
                return
            match = _CLAIM.fullmatch(self.path)
            if match:
                proof = self._agent_secret()
                if proof is None:
                    self._reply(404, {"error": "session unavailable"})
                    return
                try:
                    key = broker.claim(session_id=match.group(1),
                                       agent_secret=proof)
                except EnrollmentError:
                    self._reply(404, {"error": "session unavailable"})
                    return
                self._reply(200, {"auth_key": key})
                return
            # No operator approval route can be reached through this server.
            self._reply(404, {"error": "not found"})

        def do_GET(self) -> None:
            if "?" in self.path:
                self._reply(404, {"error": "not found"})
                return
            match = _SESSION.fullmatch(self.path)
            if match:
                proof = self._agent_secret()
                if proof is None:
                    self._reply(404, {"error": "session unavailable"})
                    return
                try:
                    state = broker.agent_state(session_id=match.group(1),
                                               agent_secret=proof)
                except EnrollmentError:
                    self._reply(404, {"error": "session unavailable"})
                    return
                self._reply(200, {"state": state})
                return
            self._reply(404, {"error": "not found"})

    return Handler


def create_loopback_server(
    broker: EnrollmentBroker, *, port: int = 0
) -> ThreadingHTTPServer:
    """No configurable external bind address: cannot accidentally expose API.

    Port 0 is used by offline tests. For real usage an explicitly configured,
    authenticated and rate-limited TLS ingress must be deployed separately.
    """
    if not 0 <= port <= 65535:
        raise ValueError("invalid port")
    return ThreadingHTTPServer(("127.0.0.1", port), _handler(broker))
