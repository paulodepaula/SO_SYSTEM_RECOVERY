"""Credential smoke-check tests: zero real API traffic, no secret output."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.recovery_enrollment.check_oauth import (
    TOKEN_URL, CredentialCheckError, load_protected_file, verify_oauth_access,
)


class OAuthSmokeCheckTests(unittest.TestCase):
    def test_token_exchange_checks_minimum_scope_without_creating_keys(self):
        calls = []
        def fake_post(url, body, headers):
            calls.append((url, body, headers))
            return {
                "access_token": "tskey-example-token-not-real-100001",
                "token_type": "Bearer",
                "scope": "auth_keys",
            }
        state = verify_oauth_access("client-test", "secret-test", post=fake_post)
        self.assertEqual(state, "oauth_auth_keys_valid")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], TOKEN_URL)
        self.assertNotIn(b"/keys", calls[0][1])
        params = urllib.parse.parse_qs(calls[0][1].decode())
        self.assertEqual(params["scope"], ["auth_keys"])
        self.assertEqual(params["tags"], ["tag:redeti-recovery"])
        self.assertEqual(params["grant_type"], ["client_credentials"])

    def test_bad_scopes_and_token_rejected(self):
        for payload in (
            {"access_token": "tskey-example-token-not-real-100001",
             "token_type": "Bearer", "scope": "devices:core"},
            {"access_token": "short",
             "token_type": "Bearer", "scope": "auth_keys"},
            {"access_token": "tskey-example-token-not-real-100001",
             "token_type": "MAC", "scope": "auth_keys"},
            {"access_token": "tskey-example-token-not-real-100001",
             "token_type": "Bearer"},
            {"error": "invalid_client", "secret": "fake"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(CredentialCheckError):
                    verify_oauth_access("fake", "fake", post=lambda *args: payload)

    def test_transport_error_redacts_secret(self):
        def fail(*args):
            raise RuntimeError("secret-test appeared in upstream details")
        with self.assertRaises(CredentialCheckError) as result:
            verify_oauth_access("id", "secret-test", post=fail)
        self.assertEqual(str(result.exception), "oauth_token_exchange_failed")
        self.assertNotIn("secret-test", str(result.exception))

    def test_requires_private_root_owned_folder_and_files(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            folder.chmod(0o700)
            owner = os.getuid()
            path = folder / "oauth-client-id"
            path.write_text("client-test")
            path.chmod(0o600)
            self.assertEqual(load_protected_file(folder, "oauth-client-id",
                                                 uid=owner), "client-test")
            path.chmod(0o644)
            with self.assertRaisesRegex(CredentialCheckError, "unsafe_secret_file"):
                load_protected_file(folder, "oauth-client-id", uid=owner)
            path.chmod(0o600)
            folder.chmod(0o755)
            with self.assertRaisesRegex(CredentialCheckError, "unsafe_secret_directory"):
                load_protected_file(folder, "oauth-client-id", uid=owner)

    def test_rejects_symlink_secret(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            folder.chmod(0o700)
            (folder / "actual").write_text("fake-secret")
            (folder / "oauth-client-secret").symlink_to(folder / "actual")
            with self.assertRaisesRegex(CredentialCheckError, "unsafe_secret_file"):
                load_protected_file(folder, "oauth-client-secret", uid=os.getuid())

    def test_does_not_accept_unexpected_secret_paths(self):
        with self.assertRaisesRegex(CredentialCheckError, "invalid_file_name"):
            load_protected_file(Path("/tmp"), "../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
