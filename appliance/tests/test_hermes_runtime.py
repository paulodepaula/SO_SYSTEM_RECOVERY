"""Two-endpoint Hermes runtime tests; never calls OAuth or creates real keys."""

import http.client
import json
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.recovery_enrollment.hermes_runtime import HermesBrokerRuntime
from services.recovery_enrollment.operator_auth import (
    example_claim_for_tests, sign_example_for_tests,
)


class FakeIssuer:
    def __init__(self):
        self.calls = 0

    def issue_one_off_key(self, *, session_id):
        self.calls += 1
        return "tskey-auth-mock-only"


class UnixHttp(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost", timeout=3)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(3)
        self.sock.connect(self.path)


def request(connection, method, path, *, headers=None, body=None):
    connection.request(method, path, headers=headers or {}, body=body)
    response = connection.getresponse()
    value = response.read()
    return response.status, json.loads(value) if value else {}


class HermesRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.folder.chmod(0o700)
        self.issuer = FakeIssuer()
        self.secret = bytes(range(32))

    def tearDown(self):
        self.temp.cleanup()

    def build(self, *, enable_key_issuance=False):
        return HermesBrokerRuntime(
            issuer=self.issuer, operator_mac_secret=self.secret,
            socket_directory=self.temp.name, agent_port=0,
            enable_key_issuance=enable_key_issuance,
        )

    def test_start_stop_and_shared_authorization(self):
        # Only an explicitly enabled *synthetic* issuer can mint a mock key.
        runtime = self.build(enable_key_issuance=True)
        with self.assertRaises(RuntimeError):
            _ = runtime.agent_address
        with runtime:
            host, port = runtime.agent_address
            self.assertEqual(host, "127.0.0.1")
            self.assertGreater(port, 0)
            path = runtime.operator_socket_path
            self.assertEqual(stat.S_IMODE(Path(path).stat().st_mode), 0o600)
            self.assertTrue(stat.S_ISSOCK(Path(path).stat().st_mode))
            with self.assertRaises(RuntimeError):
                runtime.start()

            conn = http.client.HTTPConnection(host, port, timeout=3)
            try:
                status, session = request(conn, "POST", "/v1/bootstrap/sessions")
                self.assertEqual(status, 201)
                sid, agent_secret = session["session_id"], session["agent_secret"]
                route = "/v1/bootstrap/sessions/" + sid
                headers = {"Authorization": "Bearer " + agent_secret}

                self.assertEqual(request(conn, "POST", route + "/claim",
                                         headers=headers)[0], 404)
                self.assertEqual(request(conn, "GET", route, headers=headers),
                                 (200, {"state": "pending"}))
                self.assertEqual(self.issuer.calls, 0)

                payload = example_claim_for_tests(
                    sid=sid, code=session["pairing_code"],
                    now=__import__("time").time().__int__(),
                )
                assertion = sign_example_for_tests(
                    payload, mac_secret=self.secret,
                )
                operator = UnixHttp(path)
                try:
                    body = json.dumps({"assertion": assertion}).encode("ascii")
                    self.assertEqual(request(
                        operator, "POST",
                        "/v1/operator/sessions/" + sid + "/approve",
                        headers={"Content-Type": "application/json"},
                        body=body)[0], 204)
                finally:
                    operator.close()

                self.assertEqual(request(conn, "GET", route, headers=headers),
                                 (200, {"state": "approved"}))
                status, claim = request(conn, "POST", route + "/claim", headers=headers)
                self.assertEqual((status, claim["auth_key"]),
                                 (200, "tskey-auth-mock-only"))
                self.assertEqual(request(conn, "POST", route + "/claim",
                                         headers=headers)[0], 404)
                self.assertEqual(self.issuer.calls, 1)
            finally:
                conn.close()
        self.assertFalse(Path(path).exists())
        with self.assertRaises(RuntimeError):
            _ = runtime.agent_address
        runtime.close()  # idempotent

    def test_default_gate_denies_key_even_after_signed_approval(self):
        runtime = self.build()  # key issuance defaults to OFF
        with runtime:
            host, port = runtime.agent_address
            conn = http.client.HTTPConnection(host, port, timeout=3)
            try:
                status, session = request(conn, "POST", "/v1/bootstrap/sessions")
                self.assertEqual(status, 201)
                sid = session["session_id"]
                route = "/v1/bootstrap/sessions/" + sid
                headers = {"Authorization": "Bearer " + session["agent_secret"]}
                assertion = sign_example_for_tests(
                    example_claim_for_tests(
                        sid=sid, code=session["pairing_code"],
                        now=int(__import__("time").time())),
                    mac_secret=self.secret,
                )
                op = UnixHttp(runtime.operator_socket_path)
                try:
                    body = json.dumps({"assertion": assertion}).encode("ascii")
                    self.assertEqual(request(
                        op, "POST",
                        "/v1/operator/sessions/" + sid + "/approve",
                        headers={"Content-Type": "application/json"},
                        body=body)[0], 204)
                finally:
                    op.close()
                self.assertEqual(request(conn, "GET", route, headers=headers),
                                 (200, {"state": "approved"}))
                self.assertEqual(request(conn, "POST", route + "/claim",
                                         headers=headers)[0], 404)
                self.assertEqual(request(conn, "GET", route, headers=headers),
                                 (200, {"state": "failed"}))
                # Critical: injected real/mocked issuer never called.
                self.assertEqual(self.issuer.calls, 0)
            finally:
                conn.close()

    def test_issuance_gate_requires_boolean(self):
        with self.assertRaises(ValueError):
            HermesBrokerRuntime(
                issuer=self.issuer, operator_mac_secret=self.secret,
                socket_directory=self.temp.name,
                enable_key_issuance="yes",
            )

    def test_bad_directory_is_fail_closed(self):
        self.folder.chmod(0o755)
        runtime = self.build()
        with self.assertRaises(PermissionError):
            runtime.start()
        self.assertFalse((self.folder / "approval.sock").exists())
        self.assertEqual(self.issuer.calls, 0)
        runtime.close()

    def test_existing_socket_file_cannot_be_overwritten(self):
        existing = self.folder / "approval.sock"
        existing.write_text("do not overwrite")
        runtime = self.build()
        with self.assertRaises(FileExistsError):
            runtime.start()
        self.assertEqual(existing.read_text(), "do not overwrite")
        self.assertEqual(self.issuer.calls, 0)
        runtime.close()

    def test_second_listener_failure_cleans_operator_socket(self):
        runtime = self.build()
        with patch(
            "services.recovery_enrollment.hermes_runtime.create_loopback_server",
            side_effect=OSError("simulated binding failure"),
        ):
            with self.assertRaises(OSError):
                runtime.start()
        self.assertFalse((self.folder / "approval.sock").exists())
        self.assertEqual(self.issuer.calls, 0)

    def test_requires_strong_operator_secret(self):
        with self.assertRaises(ValueError):
            HermesBrokerRuntime(
                issuer=self.issuer, operator_mac_secret=b"short",
                socket_directory=self.temp.name
            )


if __name__ == "__main__":
    unittest.main()
