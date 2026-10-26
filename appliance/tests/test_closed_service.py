"""Closed-mode service staging tests; no Tailscale traffic or auth keys."""
from pathlib import Path
import http.client
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.recovery_enrollment.closed_service import (
    make_closed_runtime, main, self_test,
)


class ClosedServiceTests(unittest.TestCase):
    def test_self_test_is_successful_without_real_keys(self):
        self.assertTrue(self_test())

    def test_default_session_is_pending_and_cannot_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_closed_runtime(socket_directory=directory, port=0) as runtime:
                host, port = runtime.agent_address
                self.assertEqual(host, "127.0.0.1")
                self.assertNotEqual(port, 0)
                connection = http.client.HTTPConnection(host, port, timeout=3)
                try:
                    connection.request("POST", "/v1/bootstrap/sessions")
                    result = connection.getresponse()
                    content = result.read()
                    self.assertEqual(result.status, 201)
                    data = json.loads(content)
                    self.assertRegex(data["pairing_code"], r"^[0-9]{8}$")
                    sid, secret = data["session_id"], data["agent_secret"]
                    connection.request("POST", "/v1/bootstrap/sessions/" + sid + "/claim",
                                       headers={"Authorization": "Bearer " + secret})
                    result = connection.getresponse()
                    result.read()
                    self.assertEqual(result.status, 404)
                finally:
                    connection.close()

    def test_untrusted_directory_is_rejected_before_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory).chmod(0o755)
            with self.assertRaises(PermissionError):
                with make_closed_runtime(socket_directory=directory, port=0):
                    pass

    def test_no_live_oauth_import_or_issuance_override(self):
        contents = (ROOT / "services/recovery_enrollment/closed_service.py").read_text()
        self.assertNotIn("TailscaleOAuthIssuer", contents)
        self.assertNotIn("load_protected_file(", contents)
        self.assertIn("enable_key_issuance=False", contents)
        self.assertNotIn("enable_key_issuance=True", contents)
        self.assertNotIn("0.0.0.0", contents)
        self.assertNotIn("tskey-auth-", contents)
        self.assertEqual(main(["--self-test"]), 0)

    def test_unprivileged_port_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for port in (-1, 22, 65536, True):
                with self.subTest(port=port):
                    with self.assertRaises(ValueError):
                        make_closed_runtime(socket_directory=directory, port=port)

    def test_no_automatic_systemd_enablement(self):
        unit = (ROOT / "services/recovery_enrollment/systemd/redeti-recovery-closed.service").read_text()
        self.assertIn("ExecStart=", unit)
        self.assertIn("--serve-closed", unit)
        self.assertIn("IPAddressDeny=any", unit)
        self.assertIn("IPAddressAllow=localhost", unit)
        self.assertIn("DynamicUser=yes", unit)
        self.assertIn("RuntimeDirectoryMode=0700", unit)
        self.assertNotIn("authkey", unit.lower())
        self.assertNotIn("ts-authkey", unit.lower())


if __name__ == "__main__":
    unittest.main()
