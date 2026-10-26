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

from .hermes_runtime import HermesBrokerRuntime
from .operator_auth import example_claim_for_tests, sign_example_for_tests


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
    """Exercise the actual Hermes runtime in its safe fake-issuer mode."""
    issuer = _FakeKeyIssuer()
    mac_key = bytes(range(32))  # Test-only fixture, never a deployment secret.
    with tempfile.TemporaryDirectory() as temp:
        with HermesBrokerRuntime(
            issuer=issuer,
            operator_mac_secret=mac_key,
            socket_directory=temp,
            agent_port=0,
            # Explicitly enabled only for synthetic, offline issuer.
            enable_key_issuance=True,
        ) as runtime:
            host, port = runtime.agent_address
            assert host == "127.0.0.1"
            conn = http.client.HTTPConnection(host, port, timeout=3)
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
                    now=int(__import__("time").time()),
                )
                assertion = sign_example_for_tests(
                    payload, mac_secret=mac_key,
                )
                operator_conn = _UnixHTTP(runtime.operator_socket_path)
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
                status, claimed = _request(conn, "POST", route + "/claim", headers)
                assert status == 200
                assert claimed.get("auth_key") == "tskey-auth-mock-only-do-not-use"
                assert _request(conn, "POST", route + "/claim", headers)[0] == 404
                assert issuer.calls == 1
            finally:
                conn.close()


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
