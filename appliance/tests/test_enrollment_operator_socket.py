"""Isolated AF_UNIX approval integration tests; no TCP or external services."""
import http.client
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services"))

from recovery_enrollment.core import EnrollmentBroker
from recovery_enrollment.operator_auth import (
    OperatorApprovalVerifier, example_claim_for_tests, sign_example_for_tests,
)
from recovery_enrollment.operator_socket import create_operator_socket_server

_SECRET = bytes(range(32))
_NOW = 1700000000


class FakeIssuer:
    def __init__(self):
        self.calls = 0
    def issue_one_off_key(self, *, session_id):
        self.calls += 1
        return "tskey-auth-fake"


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost", timeout=2)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


class OperatorSocketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.issuer = FakeIssuer()
        self.broker = EnrollmentBroker(self.issuer, clock=lambda: _NOW)
        self.verifier = OperatorApprovalVerifier(
            self.broker, mac_secret=_SECRET, clock=lambda: _NOW)
        self.server = create_operator_socket_server(
            self.verifier, directory=self.temp.name)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.socket_path = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=3)
        self.temp.cleanup()

    def request(self, path, body, *, method="POST", content_type="application/json"):
        headers = {"Content-Type": content_type} if content_type else {}
        # Each HTTP response deliberately closes the connection; open a
        # new local AF_UNIX connection for every independent request.
        conn = UnixHTTP(self.socket_path)
        try:
            conn.request(method, path, body=body, headers=headers)
            result = conn.getresponse()
            result.read()
            return result.status, dict(result.getheaders())
        finally:
            conn.close()

    def request_headers_only(self, path, content_length, content_type):
        # For oversized/unsupported requests the server intentionally replies
        # and closes without reading the body. Do not race that close by
        # attempting to upload a rejected payload.
        conn = socket.socket(socket.AF_UNIX)
        conn.settimeout(2)
        try:
            conn.connect(self.socket_path)
            headers = (
                f"POST {path} HTTP/1.1\\r\\n"
                "Host: localhost\\r\\n"
                f"Content-Type: {content_type}\\r\\n"
                f"Content-Length: {content_length}\\r\\n"
                "Connection: close\\r\\n\\r\\n"
            ).replace("\\r", "\r").replace("\\n", "\n")
            conn.sendall(headers.encode("ascii"))
            first = conn.recv(1024)
            return int(first.split(b" ", 2)[1])
        finally:
            conn.close()

    def test_verified_operator_approval_over_private_socket(self):
        r = self.broker.request(source="127.0.0.1")
        payload = example_claim_for_tests(sid=r.session_id,
                                          code=r.pairing_code, now=_NOW)
        assertion = sign_example_for_tests(payload, mac_secret=_SECRET)
        import json
        body = json.dumps({"assertion":assertion}).encode("utf-8")
        path = f"/v1/operator/sessions/{r.session_id}/approve"
        self.assertEqual(self.request(path, body)[0], 204)
        self.assertEqual(self.broker.agent_state(
            session_id=r.session_id, agent_secret=r.agent_secret), "approved")
        self.assertEqual(self.request(path, body)[0], 403)
        self.assertEqual(self.issuer.calls, 0)

    def test_proof_cannot_approve_different_session_path(self):
        a = self.broker.request(source="127.0.0.1")
        b = self.broker.request(source="127.0.0.1")
        payload = example_claim_for_tests(sid=a.session_id, code=a.pairing_code, now=_NOW)
        assertion = sign_example_for_tests(payload, mac_secret=_SECRET)
        import json
        body = json.dumps({"assertion":assertion}).encode()
        path = f"/v1/operator/sessions/{b.session_id}/approve"
        self.assertEqual(self.request(path, body)[0], 403)
        self.assertEqual(self.broker.agent_state(
            session_id=a.session_id, agent_secret=a.agent_secret), "pending")

    def test_no_http_server_routes_to_operator(self):
        self.assertEqual(self.request("/health", b"")[0], 404)
        self.assertEqual(self.request("/v1/operator/sessions/bad/approve", b"")[0], 404)
        self.assertEqual(self.request("/anything", b"", method="GET")[0], 404)

    def test_invalid_input_and_forged_auth_are_rejected(self):
        r = self.broker.request(source="127.0.0.1")
        path = f"/v1/operator/sessions/{r.session_id}/approve"
        self.assertEqual(self.request(path, b'{"assertion":"forged"}')[0], 403)
        self.assertEqual(self.request(path, b"[]")[0], 403)
        self.assertEqual(self.request(path, b'{"other":"foo"}')[0], 403)
        self.assertEqual(self.request_headers_only(path, 2, "text/plain"), 415)
        self.assertEqual(self.request_headers_only(path, 5000, "application/json"), 413)

    def test_socket_is_private_and_existing_path_is_not_overwritten(self):
        import os, stat
        path = self.server.server_address
        self.assertTrue(stat.S_ISSOCK(os.stat(path).st_mode))
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            create_operator_socket_server(self.verifier,
                                          directory=self.temp.name)

    def test_insecure_socket_directory_is_rejected(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            os.chmod(temp, 0o755)
            with self.assertRaises(PermissionError):
                create_operator_socket_server(self.verifier,
                                              directory=temp)


if __name__ == "__main__":
    unittest.main()
