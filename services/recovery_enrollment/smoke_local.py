"""Local E2E dry-run of Hermes broker without OAuth tokens or API traffic.

Run on Hermes from a reviewed repository checkout:
    python3 -m services.recovery_enrollment.smoke_local

Uses only 127.0.0.1, a temporary AF_UNIX socket and a fake Tailscale issuer.
Never writes credentials, authenticates a device or creates a real auth key.
"""
from __future__ import annotations

import http.client
import json
import socket
import tempfile
import threading

from .core import EnrollmentBroker
from .http_api import create_loopback_server
from .operator_auth import (
    OperatorApprovalVerifier, example_claim_for_tests, sign_example_for_tests,
)
from .operator_socket import create_operator_socket_server


class _FakeKeyIssuer:
    def __init__(self) -> None:
        self.calls = 0

    def issue_one_off_key(self, *, session_id: str) -> str:
        self.calls += 1
        # Synthetic key: enough to check the state machine; never valid.
        return "tskey-auth-mock-only-do-not-use"


class _UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path: str) -> None:
        super().__init__("localhost", timeout=3)
        self._path = path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._path)


def _request(conn: http.client.HTTPConnection, method: str, path: str,
             headers: dict[str, str] | None = None,
             body: bytes | None = None) -> tuple[int, dict]:
    conn.request(method, path, headers=headers or {}, body=body)
    response = conn.getresponse()
    raw = response.read()
    return response.status, json.loads(raw) if raw else {}


def check() -> None:
    issuer = _FakeKeyIssuer()
    broker = EnrollmentBroker(issuer)
    agent_server = create_loopback_server(broker, port=0)
    assert agent_server.server_address[0] == "127.0.0.1"
    agent_thread = threading.Thread(target=agent_server.serve_forever, daemon=True)
    agent_thread.start()
    try:
        with tempfile.TemporaryDirectory() as temp:
            verifier = OperatorApprovalVerifier(broker, mac_secret=bytes(range(32)))
            operator_server = create_operator_socket_server(
                verifier, directory=temp)
            operator_thread = threading.Thread(
                target=operator_server.serve_forever, daemon=True)
            operator_thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", agent_server.server_port, timeout=3)
                try:
                    status, session = _request(conn, "POST", "/v1/bootstrap/sessions")
                    assert status == 201
                    sid, proof = session["session_id"], session["agent_secret"]
                    route = "/v1/bootstrap/sessions/" + sid
                    headers = {"Authorization": "Bearer " + proof}
                    assert _request(conn, "POST", route + "/claim", headers)[0] == 404
                    assert _request(conn, "GET", route, headers) == (
                        200, {"state": "pending"})

                    payload = example_claim_for_tests(
                        sid=sid, code=session["pairing_code"],
                        now=int(__import__("time").time()))
                    assertion = sign_example_for_tests(
                        payload, mac_secret=bytes(range(32)))
                    operator_conn = _UnixHTTP(operator_server.server_address)
                    try:
                        body = json.dumps({"assertion": assertion}).encode("ascii")
                        code, _ = _request(
                            operator_conn, "POST",
                            "/v1/operator/sessions/" + sid + "/approve",
                            {"Content-Type": "application/json"}, body)
                        assert code == 204
                    finally:
                        operator_conn.close()
                    assert _request(conn, "GET", route, headers) == (
                        200, {"state": "approved"})
                    status, claimed = _request(
                        conn, "POST", route + "/claim", headers)
                    assert status == 200
                    assert claimed.get("auth_key", "").startswith(
                        "tskey-auth-mock-")
                    assert _request(conn, "POST", route + "/claim", headers)[0] == 404
                    assert issuer.calls == 1
                finally:
                    conn.close()
            finally:
                operator_server.shutdown()
                operator_server.server_close()
                operator_thread.join(timeout=4)
    finally:
        agent_server.shutdown()
        agent_server.server_close()
        agent_thread.join(timeout=4)


def main() -> int:
    try:
        check()
    except Exception:
        # Never print bearer proofs, assertions, keys, provider bodies or
        # HTTP exception details from future production integrations.
        print("FAIL: local_enrollment_integration")
        return 1
    print("PASS: local_enrollment_integration (emissor simulado; sem tokens reais)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
