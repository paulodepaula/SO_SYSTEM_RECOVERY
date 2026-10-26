"""Local-only enrollment HTTP adapter tests. Never contacts Tailscale."""
import http.client
import json
from pathlib import Path
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services"))
from recovery_enrollment.core import EnrollmentBroker
from recovery_enrollment.http_api import create_loopback_server


class FakeIssuer:
    def __init__(self):
        self.count = 0

    def issue_one_off_key(self, *, session_id):
        self.count += 1
        return "tskey-auth-example-in-memory"


class HttpAdapterTests(unittest.TestCase):
    def setUp(self):
        self.issuer = FakeIssuer()
        self.broker = EnrollmentBroker(self.issuer)
        self.server = create_loopback_server(self.broker)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.conn = http.client.HTTPConnection("127.0.0.1",
                                                self.server.server_port, timeout=3)

    def tearDown(self):
        self.conn.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, path, *, proof=None, body=None, extra_headers=None):
        headers = extra_headers or {}
        if proof is not None:
            headers = {**headers, "Authorization": "Bearer " + proof}
        self.conn.request(method, path, body=body, headers=headers)
        response = self.conn.getresponse()
        data = response.read()
        value = json.loads(data)
        return response.status, value, dict(response.getheaders())

    def test_no_public_network_binding(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_lifecycle_requires_operator_approval_and_agent_proof(self):
        status, created, headers = self.request("POST", "/v1/bootstrap/sessions")
        self.assertEqual(status, 201)
        self.assertIn("no-store", headers["Cache-Control"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        sid = created["session_id"]
        secret = created["agent_secret"]
        self.assertRegex(created["pairing_code"], r"^[0-9]{8}$")
        path = "/v1/bootstrap/sessions/" + sid
        status, _, _ = self.request("GET", path)
        self.assertEqual(status, 404)
        status, _, _ = self.request("GET", path, proof="wrong" * 8)
        self.assertEqual(status, 404)
        status, state, _ = self.request("GET", path, proof=secret)
        self.assertEqual((status, state["state"]), (200, "pending"))
        status, _, _ = self.request("POST", path + "/claim", proof=secret)
        self.assertEqual(status, 404)
        status, _, _ = self.request(
            "POST", "/v1/operator/sessions/" + sid + "/approve",
            body=b'{"pairing_code":"anything"}',
            extra_headers={"Content-Type": "application/json"})
        self.assertEqual(status, 404)
        self.assertEqual(self.issuer.count, 0)
        self.broker.approve(session_id=sid, pairing_code=created["pairing_code"],
                            operator_id="verified-operator", work_order="OS-17")
        status, key, headers = self.request("POST", path + "/claim", proof=secret)
        self.assertEqual(status, 200)
        self.assertEqual(key["auth_key"], "tskey-auth-example-in-memory")
        self.assertIn("no-store", headers["Cache-Control"])
        status, _, _ = self.request("POST", path + "/claim", proof=secret)
        self.assertEqual(status, 404)
        self.assertEqual(self.issuer.count, 1)

    def test_does_not_accept_proofs_in_query_or_body(self):
        status, created, _ = self.request("POST", "/v1/bootstrap/sessions")
        sid, secret = created["session_id"], created["agent_secret"]
        root = "/v1/bootstrap/sessions/" + sid
        self.assertEqual(self.request("GET", root + "?token=" + secret)[0], 404)
        self.assertEqual(self.request("POST", root + "/claim",
                                      body=secret.encode("ascii"))[0], 400)
        self.assertEqual(self.request("POST", "/v1/bootstrap/sessions",
                         extra_headers={"Transfer-Encoding": "chunked"})[0], 400)
        self.assertEqual(self.issuer.count, 0)

    def test_operator_endpoint_is_not_exposed(self):
        self.assertEqual(
            self.request("POST", "/v1/operator/sessions/placeholder/approve")[0],
            404)
        self.assertEqual(self.request("GET", "/health")[0], 404)


if __name__ == "__main__":
    unittest.main()
