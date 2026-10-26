"""Closed-gate Hermes service staging: local listeners, zero real key issuance.

Use ONLY for isolated homologation. This module intentionally has no
Tailscale/OAuth imports and never opens an external listener.

Commands from a reviewed repository checkout:
  python3 -m services.recovery_enrollment.closed_service --self-test
  python3 -m services.recovery_enrollment.closed_service --serve-closed \
      --socket-directory /run/redeti-recovery --port 39081

--serve-closed needs a pre-existing private directory owned by the caller
(mode 0700). The operator signing key is intentionally generated in RAM and
discarded at shutdown; the Service Desk has NO signing integration here.
Nothing in this service can issue an auth key.
"""
from __future__ import annotations

import argparse
import http.client
import json
from pathlib import Path
import secrets
import signal
import tempfile
import threading

from .hermes_runtime import HermesBrokerRuntime


class _UnavailableIssuer:
    """Defense in depth even if runtime's deny-by-default guard regresses."""

    def issue_one_off_key(self, *, session_id: str) -> str:
        raise RuntimeError("credential issuance is prohibited in closed mode")


def make_closed_runtime(*, socket_directory: str, port: int = 39081) -> HermesBrokerRuntime:
    """Non-network-configurable local-only runtime with throwaway RAM secret."""
    # port=0 asks the OS for an ephemeral port; only offline tests use it.
    if type(port) is not int or port != 0 and not 1024 <= port <= 65535:
        raise ValueError("invalid local port")
    return HermesBrokerRuntime(
        issuer=_UnavailableIssuer(),
        operator_mac_secret=secrets.token_bytes(32),
        socket_directory=socket_directory,
        agent_port=port,
        enable_key_issuance=False,  # do not bypass: no real OAuth in this module
    )


def self_test() -> bool:
    """Prove a pending session cannot claim credentials; no Tailscale traffic."""
    with tempfile.TemporaryDirectory() as tmp:
        # TemporaryDirectory is owned by us with mode 0700.
        with make_closed_runtime(socket_directory=tmp, port=0) as server:
            http = http.client.HTTPConnection(*server.agent_address, timeout=3)
            try:
                http.request("POST", "/v1/bootstrap/sessions")
                response = http.getresponse()
                body = response.read()
                if response.status != 201:
                    return False
                receipt = json.loads(body)
                session_id = receipt["session_id"]
                secret = receipt["agent_secret"]
                http.request(
                    "POST", f"/v1/bootstrap/sessions/{session_id}/claim",
                    headers={"Authorization": "Bearer " + secret},
                )
                rejected = http.getresponse()
                rejected.read()
                if rejected.status != 404:
                    return False
            finally:
                http.close()
            return server.agent_address[0] == "127.0.0.1"


def serve_closed(*, socket_directory: str, port: int) -> None:
    """Run until SIGTERM/SIGINT and then close both listeners atomically."""
    directory = Path(socket_directory)
    if not directory.exists():
        raise RuntimeError("private runtime directory absent")
    finished = threading.Event()
    def stop(_sig: int, _frame: object) -> None:
        finished.set()
    # Do not override signals when imported/used by a test in a thread.
    previous_term = signal.signal(signal.SIGTERM, stop)
    previous_int = signal.signal(signal.SIGINT, stop)
    try:
        with make_closed_runtime(socket_directory=str(directory), port=port) as runtime:
            print(
                f"REDETI_BROKER_CLOSED_READY: {runtime.agent_address[0]}:"
                f"{runtime.agent_address[1]} (issuance=DENIED, operator=AF_UNIX)",
                flush=True,
            )
            finished.wait()
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes private closed-mode broker")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--serve-closed", action="store_true")
    parser.add_argument("--socket-directory", default="/run/redeti-recovery")
    parser.add_argument("--port", type=int, default=39081)
    args = parser.parse_args(argv)
    if args.self_test:
        try:
            ok = self_test()
        except Exception:
            ok = False
        print("PASS: closed_mode_no_key_issuance" if ok else "FAIL: closed_mode_self_test")
        return 0 if ok else 1
    try:
        serve_closed(socket_directory=args.socket_directory, port=args.port)
    except Exception:
        # No exception texts: a future transport might include sensitive data.
        print("FAIL: closed_service_startup")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
