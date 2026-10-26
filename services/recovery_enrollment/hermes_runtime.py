"""Hermes broker lifecycle: one state machine, two strictly local endpoints.

This is a reusable, dependency-injected runtime, not a daemon/service unit.
No network exposure, OAuth token exchange or real auth-key creation occurs
merely by importing or constructing this runtime. A future reviewed launcher
may supply the real OAuth issuer and a *protected* operator-signing secret,
after Service Desk authentication, host permissions and audit are homologated.

Callers own the private socket directory and MUST keep it 0700.
"""

from __future__ import annotations

import threading
from typing import Protocol

from .core import EnrollmentBroker, KeyIssuer
from .http_api import create_loopback_server
from .operator_auth import OperatorApprovalVerifier
from .operator_socket import create_operator_socket_server


class _Server(Protocol):
    server_address: object

    def serve_forever(self, poll_interval: float = 0.5) -> None: ...
    def shutdown(self) -> None: ...
    def server_close(self) -> None: ...


class HermesBrokerRuntime:
    """Manage both listeners with shared state and fail-closed cleanup.

    - Agent HTTP: bound exclusively to IPv4 127.0.0.1 (no HTTPS/public route).
    - Operator HTTP: local UNIX socket in an owned private directory.
    - Approval and agent claim share a single EnrollmentBroker instance.
    - No background thread or listener exists until start() is called.
    - A failed start() closes already-created listeners, not leaving sockets.
    """

    def __init__(
        self, *, issuer: KeyIssuer, operator_mac_secret: bytes,
        socket_directory: str, agent_port: int = 0,
    ) -> None:
        if not isinstance(operator_mac_secret, bytes) or len(operator_mac_secret) < 32:
            raise ValueError("invalid operator secret")
        self._broker = EnrollmentBroker(issuer)
        self._verifier = OperatorApprovalVerifier(
            self._broker, mac_secret=operator_mac_secret,
        )
        self._socket_directory = socket_directory
        self._agent_port = agent_port
        self._agent: _Server | None = None
        self._operator: _Server | None = None
        self._threads: list[threading.Thread] = []
        self._running_servers: list[_Server] = []
        self._started = False

    @property
    def agent_address(self) -> tuple[str, int]:
        if not self._started or self._agent is None:
            raise RuntimeError("broker not running")
        return self._agent.server_address  # type: ignore[return-value]

    @property
    def operator_socket_path(self) -> str:
        if not self._started or self._operator is None:
            raise RuntimeError("broker not running")
        return self._operator.server_address  # type: ignore[return-value]

    def start(self) -> None:
        if self._started or self._agent is not None or self._operator is not None:
            raise RuntimeError("broker has already been started")
        try:
            # Bind the operator socket first: reject unsafe directory before
            # creating the agent listener. Agent is always bound to loopback.
            self._operator = create_operator_socket_server(
                self._verifier, directory=self._socket_directory,
            )
            self._agent = create_loopback_server(
                self._broker, port=self._agent_port,
            )
            pairs = [
                (self._operator, threading.Thread(
                    target=self._operator.serve_forever,
                    name="redeti-operator", daemon=True)),
                (self._agent, threading.Thread(
                    target=self._agent.serve_forever,
                    name="redeti-agent", daemon=True)),
            ]
            for server, thread in pairs:
                thread.start()
                self._running_servers.append(server)
                self._threads.append(thread)
            self._started = True
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        # shutdown() is safe only for listeners whose serve_forever() has
        # started; otherwise it can block indefinitely. Track starts
        # individually to handle a partially failed thread start.
        for server in self._running_servers:
            server.shutdown()
        for server in (self._agent, self._operator):
            if server is not None:
                server.server_close()
        for thread in self._threads:
            thread.join(timeout=4)
        self._threads = []
        self._running_servers = []
        self._agent = None
        self._operator = None
        self._started = False

    def __enter__(self) -> "HermesBrokerRuntime":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
