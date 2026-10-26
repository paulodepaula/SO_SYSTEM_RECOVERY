"""Offline signed-approval contract tests. No Service Desk or Tailscale calls."""
from pathlib import Path
import copy
import json
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services"))
from recovery_enrollment.core import EnrollmentBroker, EnrollmentError
from recovery_enrollment.operator_auth import (
    OperatorApprovalVerifier, OperatorAuthError,
    example_claim_for_tests, sign_example_for_tests,
)

SECRET = bytes(range(32))


class FakeIssuer:
    def __init__(self):
        self.calls = 0
    def issue_one_off_key(self, *, session_id):
        self.calls += 1
        return "tskey-auth-FAKE"


class OperatorApprovalTests(unittest.TestCase):
    def setUp(self):
        self.now = 1700000000
        self.issuer = FakeIssuer()
        self.broker = EnrollmentBroker(self.issuer, clock=lambda: self.now)
        self.verifier = OperatorApprovalVerifier(
            self.broker, mac_secret=SECRET, clock=lambda: self.now
        )
        self.receipt = self.broker.request(source="127.0.0.1")
        self.payload = example_claim_for_tests(
            sid=self.receipt.session_id,
            code=self.receipt.pairing_code,
            now=self.now,
        )

    def assertion(self, data=None, secret=SECRET):
        return sign_example_for_tests(
            self.payload if data is None else data, mac_secret=secret
        )

    def test_signed_operator_can_approve_one_pending_pairing(self):
        self.verifier.approve_signed(self.assertion())
        self.assertEqual(
            self.broker.agent_state(session_id=self.receipt.session_id,
                                    agent_secret=self.receipt.agent_secret),
            "approved")
        self.assertEqual(self.issuer.calls, 0)
        result = self.broker.claim(
            session_id=self.receipt.session_id,
            agent_secret=self.receipt.agent_secret)
        self.assertEqual(result, "tskey-auth-FAKE")
        self.assertEqual(self.issuer.calls, 1)

    def test_invalid_signature_and_unsigned_json_denied(self):
        for request in (
            json.dumps(self.payload),
            self.assertion(secret=b"x" * 32),
            self.assertion() + "x",
            "",
        ):
            with self.subTest(request=request[:10]):
                with self.assertRaises(OperatorAuthError):
                    self.verifier.approve_signed(request)
        self.assertEqual(self.issuer.calls, 0)
        self.assertEqual(self.broker.agent_state(
            session_id=self.receipt.session_id,
            agent_secret=self.receipt.agent_secret), "pending")

    def test_expired_future_or_oversized_assertions_denied(self):
        for iat, exp in (
            (self.now - 100, self.now - 1),
            (self.now + 11, self.now + 80),
            (self.now - 200, self.now - 190),
            (self.now, self.now + 500),
        ):
            payload = {**self.payload, "iat": iat, "exp": exp}
            with self.assertRaises(OperatorAuthError):
                self.verifier.approve_signed(self.assertion(payload))
        with self.assertRaises(OperatorAuthError):
            self.verifier.approve_signed(self.assertion() + "Z" * 7000)

    def test_forged_role_audience_permission_order_and_code_denied(self):
        cases = [
            {"role": "TECNICO"},
            {"role": ["ADMIN"]},
            {"permission": "OS_READ"},
            {"aud": "other-service"},
            {"iss": "external"},
            {"os_id": ""},
            {"operator": ""},
            {"code": "00000000" if self.receipt.pairing_code != "00000000" else "99999999"},
            {"sid": "wrong-" + self.receipt.session_id},
            {"extra": "not-allowed"},
            {"version": 2},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                altered = {**self.payload, **changes}
                with self.assertRaises(OperatorAuthError):
                    self.verifier.approve_signed(self.assertion(altered))
        self.assertEqual(self.issuer.calls, 0)

    def test_replay_rejected_after_approval(self):
        signed = self.assertion()
        self.verifier.approve_signed(signed)
        with self.assertRaises(OperatorAuthError):
            self.verifier.approve_signed(signed)

    def test_wrong_pairing_code_consumes_nonce(self):
        bad = {**self.payload, "code": "12345678"
               if self.receipt.pairing_code != "12345678" else "87654321"}
        signed = self.assertion(bad)
        with self.assertRaises(OperatorAuthError):
            self.verifier.approve_signed(signed)
        with self.assertRaises(OperatorAuthError):
            self.verifier.approve_signed(signed)

    def test_concurrent_duplicate_approval_is_rejected(self):
        signed = self.assertion()
        result = []
        def approve():
            try:
                self.verifier.approve_signed(signed)
                result.append("ok")
            except OperatorAuthError:
                result.append("denied")
        threads = [threading.Thread(target=approve) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(result.count("ok"), 1)
        self.assertEqual(result.count("denied"), 7)

    def test_missing_or_weak_secret_fails(self):
        for value in (b"", b"short"):
            with self.assertRaises(ValueError):
                OperatorApprovalVerifier(self.broker, mac_secret=value)

    def test_no_operator_approval_via_untrusted_http(self):
        from recovery_enrollment.http_api import create_loopback_server
        import http.client
        import threading
        srv = create_loopback_server(self.broker)
        worker = threading.Thread(target=srv.serve_forever, daemon=True)
        worker.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=2)
            connection.request("POST", "/v1/operator/sessions/" +
                               self.receipt.session_id + "/approve",
                               body=b"{}", headers={"Content-Type":"application/json"})
            res = connection.getresponse()
            res.read()
            self.assertEqual(res.status, 404)
            connection.close()
        finally:
            srv.shutdown()
            srv.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
