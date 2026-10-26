"""Live auth-key lifecycle smoke unit tests; use fake transport, never API."""
import json
from pathlib import Path
import sys
import unittest
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.recovery_enrollment.check_authkey_lifecycle import (
    LifecycleCheckError, check_lifecycle, main,
)
from services.recovery_enrollment.tailscale_oauth import (
    TOKEN_URL, CREATE_KEY_URL, RECOVERY_TAG,
)


class FakeTransport:
    def __init__(self, *, bad_capabilities=False, fail_revoke=False,
                 fail_create=False, missing_id=False, fail_token=False):
        self.calls = []
        self.bad_capabilities = bad_capabilities
        self.fail_revoke = fail_revoke
        self.fail_create = fail_create
        self.missing_id = missing_id
        self.fail_token = fail_token

    def __call__(self, method, url, body, headers):
        self.calls.append((method, url, body, headers))
        if url == TOKEN_URL:
            if self.fail_token:
                raise RuntimeError("upstream secret-test")
            return {"access_token": "fake-bearer-value-with-sufficient-length",
                    "token_type": "Bearer", "scope": "auth_keys"}
        if method == "POST":
            if self.fail_create:
                raise RuntimeError("secret-test on create")
            obj = json.loads(body)
            assert obj["expirySeconds"] == 900
            assert obj["description"] == "redeti-recovery-smoke"
            assert obj["capabilities"]["devices"]["create"]["preauthorized"] is False
            caps = obj["capabilities"]
            if self.bad_capabilities:
                caps["devices"]["create"]["reusable"] = True
            response = {
                "key": "tskey-auth-fake-do-not-use",
                "capabilities": caps,
            }
            if not self.missing_id:
                response["id"] = "k123456CNTRL"
            return response
        if method == "DELETE":
            if self.fail_revoke:
                raise RuntimeError("secret-test in server response")
            return {}
        raise AssertionError("Unexpected HTTP path")

    def operations(self):
        return [method for method, _, _, _ in self.calls]


class LifecycleTests(unittest.TestCase):
    def test_issued_and_revoked_once_with_exact_tag(self):
        fake = FakeTransport()
        self.assertEqual(
            check_lifecycle("fake-id", "fake-secret", transport=fake),
            "real_authkey_created_and_revoked",
        )
        self.assertEqual(fake.operations(), ["POST", "POST", "DELETE"])
        self.assertEqual(fake.calls[0][1], TOKEN_URL)
        self.assertEqual(fake.calls[1][1], CREATE_KEY_URL)
        self.assertEqual(fake.calls[2][1], CREATE_KEY_URL + "/k123456CNTRL")
        form = urllib.parse.parse_qs(fake.calls[0][2].decode())
        self.assertEqual(form["scope"], ["auth_keys"])
        self.assertEqual(form["tags"], [RECOVERY_TAG])
        req = json.loads(fake.calls[1][2])
        create = req["capabilities"]["devices"]["create"]
        self.assertEqual(create["tags"], [RECOVERY_TAG])
        self.assertIs(create["reusable"], False)
        self.assertIs(create["ephemeral"], True)
        self.assertIs(create["preauthorized"], False)

    def test_invalid_returned_key_is_still_revoked(self):
        fake = FakeTransport(bad_capabilities=True)
        with self.assertRaisesRegex(LifecycleCheckError, "created_key_capabilities_invalid"):
            check_lifecycle("fake-id", "fake-secret", transport=fake)
        self.assertEqual(fake.operations(), ["POST", "POST", "DELETE"])

    def test_revoke_failed_is_never_reported_pass(self):
        fake = FakeTransport(fail_revoke=True)
        with self.assertRaisesRegex(
            LifecycleCheckError, "revocation_unverified_review_keys_panel"
        ) as err:
            check_lifecycle("fake-id", "fake-secret", transport=fake)
        self.assertNotIn("secret-test", str(err.exception))
        self.assertEqual(fake.operations(), ["POST", "POST", "DELETE"])

    def test_revocation_http_status_is_sanitized_and_no_retry(self):
        # Simulated status: no real Tailscale requests or keys.
        for status in (403, 404, 429, 500):
            fake = FakeTransport()
            original = fake.__call__
            def transport(method, url, body, headers):
                if method == "DELETE":
                    fake.calls.append((method, url, body, headers))
                    raise LifecycleCheckError(f"api_http_{status}")
                return original(method, url, body, headers)
            with self.subTest(status=status):
                with self.assertRaises(LifecycleCheckError) as err:
                    check_lifecycle("fake-id", "fake-secret",
                                    transport=transport)
                self.assertEqual(
                    str(err.exception),
                    f"revocation_api_http_{status}_review_keys_panel",
                )
                self.assertEqual(fake.operations(), ["POST", "POST", "DELETE"])
                self.assertNotIn("fake-secret", str(err.exception))

    def test_no_id_no_retry_and_safe_failure(self):
        fake = FakeTransport(missing_id=True)
        with self.assertRaisesRegex(LifecycleCheckError,
                                    "creation_unknown_review_keys_panel"):
            check_lifecycle("fake-id", "fake-secret", transport=fake)
        self.assertEqual(fake.operations(), ["POST", "POST"])

    def test_failed_creation_must_not_auto_retry(self):
        fake = FakeTransport(fail_create=True)
        with self.assertRaisesRegex(LifecycleCheckError,
                                    "creation_unknown_review_keys_panel"):
            check_lifecycle("fake-id", "fake-secret", transport=fake)
        self.assertEqual(fake.operations(), ["POST", "POST"])

    def test_failed_oauth_never_calls_create_key(self):
        fake = FakeTransport(fail_token=True)
        with self.assertRaisesRegex(LifecycleCheckError, "oauth_exchange_failed"):
            check_lifecycle("fake-id", "fake-secret", transport=fake)
        self.assertEqual(fake.operations(), ["POST"])

    def test_requires_explicit_operator_invocation(self):
        self.assertEqual(main(argv=[]), 2)
        self.assertEqual(main(argv=["--wrong"]), 2)


if __name__ == "__main__":
    unittest.main()
