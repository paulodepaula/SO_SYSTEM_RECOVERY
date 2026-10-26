"""Offline Hermes enrollment tests; fake issuer, no real credentials or API calls."""
import json
from pathlib import Path
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services"))

from recovery_enrollment.core import EnrollmentBroker, EnrollmentError
from recovery_enrollment.tailscale_oauth import (
    CREATE_KEY_URL, RECOVERY_TAG, TOKEN_URL, TailscaleOAuthIssuer,
)


class FakeIssuer:
    def __init__(self, *, fail=False):
        self.calls = 0
        self.fail = fail

    def issue_one_off_key(self, *, session_id):
        self.calls += 1
        if self.fail:
            raise RuntimeError("UPSTREAM SECRET ERROR - must never be returned")
        return "tskey-auth-fake"


class EnrollmentCoreTests(unittest.TestCase):
    def setUp(self):
        self.time = 50000.0
        self.issuer = FakeIssuer()
        self.events = []
        self.broker = EnrollmentBroker(self.issuer, clock=lambda: self.time,
                                        audit=lambda event, sid: self.events.append((event, sid)))

    def test_approval_and_claim_are_two_independent_secrets(self):
        receipt = self.broker.request(source="test-ip")
        self.assertEqual(self.broker.agent_state(session_id=receipt.session_id, agent_secret=receipt.agent_secret), "pending")
        self.assertRegex(receipt.pairing_code, r"^[0-9]{8}$")
        self.assertGreaterEqual(len(receipt.agent_secret), 32)
        with self.assertRaises(EnrollmentError):
            self.broker.claim(session_id=receipt.session_id,
                              agent_secret=receipt.agent_secret)
        with self.assertRaises(EnrollmentError):
            self.broker.approve(session_id=receipt.session_id,
                                pairing_code="0000000x", operator_id="technician",
                                work_order="OS-14")
        self.assertEqual(self.issuer.calls, 0)
        self.broker.approve(session_id=receipt.session_id, pairing_code=receipt.pairing_code,
                            operator_id="technician", work_order="OS-14")
        with self.assertRaises(EnrollmentError):
            self.broker.claim(session_id=receipt.session_id, agent_secret="wrong")
        key = self.broker.claim(session_id=receipt.session_id,
                                agent_secret=receipt.agent_secret)
        self.assertEqual(key, "tskey-auth-fake")
        self.assertEqual(self.broker.agent_state(session_id=receipt.session_id, agent_secret=receipt.agent_secret), "consumed")
        self.assertEqual(self.issuer.calls, 1)
        with self.assertRaises(EnrollmentError):
            self.broker.claim(session_id=receipt.session_id,
                              agent_secret=receipt.agent_secret)
        self.assertEqual(self.issuer.calls, 1)
        for event, sid in self.events:
            self.assertEqual(sid, receipt.session_id)
            self.assertNotIn(receipt.agent_secret, event)
            self.assertNotIn(key, event)

    def test_expiration_prevents_approval_or_issuance(self):
        r = self.broker.request(source="test")
        self.time += 181
        with self.assertRaises(EnrollmentError):
            self.broker.approve(session_id=r.session_id, pairing_code=r.pairing_code,
                                operator_id="tech", work_order="OS-15")
        self.assertEqual(self.broker.agent_state(session_id=r.session_id, agent_secret=r.agent_secret), "expired")
        self.assertEqual(self.issuer.calls, 0)

    def test_expiration_after_approval_prevents_claim(self):
        r = self.broker.request(source="test")
        self.broker.approve(session_id=r.session_id, pairing_code=r.pairing_code,
                            operator_id="tech", work_order="OS-15")
        self.time += 181
        with self.assertRaises(EnrollmentError):
            self.broker.claim(session_id=r.session_id, agent_secret=r.agent_secret)
        self.assertEqual(self.issuer.calls, 0)

    def test_status_requires_correct_agent_proof(self):
        r = self.broker.request(source="test")
        with self.assertRaises(EnrollmentError):
            self.broker.agent_state(session_id=r.session_id, agent_secret="wrong")
        with self.assertRaises(EnrollmentError):
            self.broker.agent_state(session_id=r.session_id, agent_secret="\N{SNOWMAN}")
        self.assertEqual(
            self.broker.agent_state(session_id=r.session_id,
                                    agent_secret=r.agent_secret), "pending")

    def test_global_rate_limit_prevents_distributed_requests(self):
        issuer = FakeIssuer()
        broker = EnrollmentBroker(issuer, clock=lambda: self.time,
                                  max_requests_per_source=10,
                                  max_requests_global=3)
        for i in range(3):
            broker.request(source="source-" + str(i))
        with self.assertRaisesRegex(EnrollmentError, "rate limit"):
            broker.request(source="different-source")

    def test_rate_limits_by_trusted_source(self):
        for i in range(6):
            self.broker.request(source="site-a")
        with self.assertRaisesRegex(EnrollmentError, "rate limit"):
            self.broker.request(source="site-a")
        self.broker.request(source="site-b")
        self.time += 601
        self.broker.request(source="site-a")

    def test_approval_requires_operator_and_work_order(self):
        r = self.broker.request(source="test")
        for operator, order in (("", "OS-3"), ("tech", "")):
            with self.assertRaises(EnrollmentError):
                self.broker.approve(session_id=r.session_id,
                                    pairing_code=r.pairing_code,
                                    operator_id=operator, work_order=order)
        self.assertEqual(self.broker.agent_state(session_id=r.session_id, agent_secret=r.agent_secret), "pending")

    def test_upstream_failure_is_final_and_redacted(self):
        issuer = FakeIssuer(fail=True)
        broker = EnrollmentBroker(issuer, clock=lambda: self.time)
        r = broker.request(source="test")
        broker.approve(session_id=r.session_id, pairing_code=r.pairing_code,
                       operator_id="tech", work_order="OS-16")
        with self.assertRaises(EnrollmentError) as ctx:
            broker.claim(session_id=r.session_id, agent_secret=r.agent_secret)
        self.assertEqual(str(ctx.exception), "enrollment failed")
        with self.assertRaises(EnrollmentError):
            broker.claim(session_id=r.session_id, agent_secret=r.agent_secret)
        self.assertEqual(issuer.calls, 1)
        self.assertEqual(broker.agent_state(session_id=r.session_id, agent_secret=r.agent_secret), "failed")

    def test_simultaneous_claims_only_issue_one_key(self):
        r = self.broker.request(source="test")
        self.broker.approve(session_id=r.session_id, pairing_code=r.pairing_code,
                            operator_id="tech", work_order="OS-20")
        outcomes = []
        def run():
            try:
                outcomes.append(self.broker.claim(session_id=r.session_id,
                                                  agent_secret=r.agent_secret))
            except EnrollmentError:
                outcomes.append("denied")
        workers = [threading.Thread(target=run) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual(outcomes.count("tskey-auth-fake"), 1)
        self.assertEqual(outcomes.count("denied"), 7)
        self.assertEqual(self.issuer.calls, 1)

    def test_no_http_listener_or_iso_delivery(self):
        # This is a library and not a public enrollment endpoint yet.
        compose = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        self.assertNotIn("services/recovery_enrollment", compose)


class OAuthIssuerTests(unittest.TestCase):
    def test_create_minimum_scope_ephemeral_single_use_key(self):
        captured = []
        def fake_transport(url, body, headers):
            captured.append((url, body, headers))
            if url == TOKEN_URL:
                return {"access_token": "test-access-token-for-mocked-issuer"}
            return {
                "key": "tskey-auth-fake",
                "capabilities": {"devices": {"create": {
                    "reusable": False, "ephemeral": True,
                    "preauthorized": True, "tags": [RECOVERY_TAG]
                }}},
            }
        issuer = TailscaleOAuthIssuer("test-id", "test-secret", transport=fake_transport)
        self.assertNotIn("test-secret", repr(issuer))
        self.assertEqual(issuer.issue_one_off_key(session_id="dummy"), "tskey-auth-fake")
        self.assertEqual([call[0] for call in captured], [TOKEN_URL, CREATE_KEY_URL])
        self.assertIn(b"grant_type=client_credentials", captured[0][1])
        self.assertIn(b"scope=auth_keys", captured[0][1])
        self.assertIn(b"tags=tag%3Aredeti-recovery", captured[0][1])
        data = json.loads(captured[1][1])
        create = data["capabilities"]["devices"]["create"]
        self.assertEqual(create["tags"], ["tag:redeti-recovery"])
        self.assertIs(create["reusable"], False)
        self.assertIs(create["ephemeral"], True)
        self.assertIs(create["preauthorized"], True)
        self.assertEqual(data["expirySeconds"], 900)
        self.assertEqual(captured[1][2]["Authorization"],
                         "Bearer test-access-token-for-mocked-issuer")
        self.assertNotIn(b"test-secret", captured[1][1])

    def test_refuses_unsafe_key_capabilities_without_secret_log(self):
        def unsafe(url, body, headers):
            if url == TOKEN_URL:
                return {"access_token": "test-access-token-for-mocked-issuer"}
            return {"key": "tskey-auth-fake",
                    "capabilities": {"devices": {"create": {
                        "reusable": True, "ephemeral": False, "tags": ["tag:admin"]
                    }}}}
        issuer = TailscaleOAuthIssuer("test-id", "test-secret", transport=unsafe)
        with self.assertRaisesRegex(RuntimeError, "^Tailscale enrollment unavailable$"):
            issuer.issue_one_off_key(session_id="dummy")


if __name__ == "__main__":
    unittest.main()
