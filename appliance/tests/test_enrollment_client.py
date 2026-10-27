"""Offline Recovery Agent enrollment tests; no Hermes/Tailscale traffic."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "redeti_enrollment_client", ROOT / "appliance" / "remote" / "enrollment_client.py"
)
assert _SPEC is not None
assert _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
EnrollmentClient = _MODULE.EnrollmentClient
EnrollmentClientError = _MODULE.EnrollmentClientError
VpnState = _MODULE.VpnState
write_status = _MODULE.write_status


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.states = ["pending", "approved"]

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers), body))
        if method == "POST" and url.endswith("/sessions"):
            return {
                "session_id": "S" * 24,
                "pairing_code": "12345678",
                "agent_secret": "A" * 40,
                "expires_at": 2000,
            }
        if method == "GET":
            return {"state": self.states.pop(0)}
        if method == "POST" and url.endswith("/claim"):
            return {"auth_key": "tskey-auth-ephemeral-test"}
        raise AssertionError("unexpected transport call")


class EnrollmentClientTests(unittest.TestCase):
    def build(self, transport=None, now=1000):
        return EnrollmentClient(
            "https://enrollment.example/v1/bootstrap",
            transport=transport or FakeTransport(),
            clock=lambda: now,
        )

    def test_network_failure_does_not_contact_broker(self):
        transport = FakeTransport()
        client = self.build(transport)
        self.assertEqual(client.start(network_available=False).state, VpnState.SEM_REDE)
        self.assertEqual(transport.calls, [])

    def test_full_simulated_pairing_claim_and_cleanup(self):
        transport = FakeTransport()
        client = self.build(transport)
        status = client.start(network_available=True)
        self.assertEqual(status.state, VpnState.AGUARDANDO_AUTORIZACAO)
        self.assertEqual(status.pairing_code, "12345678")
        self.assertNotIn("agent_secret", status.public_json())
        self.assertEqual(client.poll().state, VpnState.AGUARDANDO_AUTORIZACAO)
        self.assertEqual(client.poll().state, VpnState.AUTORIZADO)
        self.assertEqual(client.claim_auth_key(), "tskey-auth-ephemeral-test")
        self.assertEqual(client.consume_auth_key(), "tskey-auth-ephemeral-test")
        with self.assertRaises(EnrollmentClientError):
            client.consume_auth_key()
        self.assertEqual(client.connected().state, VpnState.CONECTADO)
        self.assertEqual(client.close().state, VpnState.SESSAO_ENCERRADA)
        self.assertNotIn("tskey-auth", str(client.status.public_json()))

    def test_claim_requires_approval_and_failed_claim_erases_state(self):
        client = self.build()
        client.start(network_available=True)
        with self.assertRaises(EnrollmentClientError):
            client.claim_auth_key()
        client.poll()
        client.poll()
        with self.assertRaises(EnrollmentClientError):
            # A malformed provider response must fail closed.
            client._transport = lambda *args: {"auth_key": "not-a-key"}
            client.claim_auth_key()
        self.assertEqual(client.status.state, VpnState.FALHA)
        self.assertNotIn("tskey-auth", str(client.status.public_json()))

    def test_expiry_and_poll_limit_fail_closed(self):
        transport = FakeTransport()
        now = [1000]
        client = EnrollmentClient(
            "https://enrollment.example/v1/bootstrap",
            transport=transport,
            clock=lambda: now[0],
            max_polls=1,
        )
        client.start(network_available=True)
        self.assertEqual(client.poll().state, VpnState.AGUARDANDO_AUTORIZACAO)
        self.assertEqual(client.poll().state, VpnState.FALHA)
        self.assertEqual(client.status.reason, "authorization_expired")
        self.assertEqual(client._agent_secret, "")

    def test_endpoint_must_be_https_without_credentials_or_query(self):
        for endpoint in (
            "http://enrollment.example/v1/bootstrap",
            "https://user:secret@enrollment.example/v1/bootstrap",
            "https://enrollment.example/v1/bootstrap?x=1",
        ):
            with self.assertRaises(ValueError):
                EnrollmentClient(endpoint)

    def test_status_writer_contains_only_public_fields(self):
        client = self.build()
        status = client.start(network_available=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "enrollment-status.json"
            write_status(path, status)
            content = path.read_text()
            self.assertIn("pairing_code", content)
            self.assertNotIn("agent_secret", content)
            self.assertNotIn("tskey-auth", content)
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
