"""Read-only Tailscale auth-key inventory tests (all API responses mocked)."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.recovery_enrollment.inspect_smoke_keys import (
    InventoryError, inventory_smoke_keys,
)
from services.recovery_enrollment.tailscale_oauth import (
    TOKEN_URL, CREATE_KEY_URL, RECOVERY_TAG,
)

NOW = datetime(2026, 10, 26, 18, 0, tzinfo=timezone.utc)


class MockAPI:
    def __init__(self, entries):
        self.entries = entries
        self.calls = []

    def __call__(self, method, url, data, headers):
        self.calls.append((method, url))
        if url == TOKEN_URL:
            return {
                "access_token": "fake-access-token-long-enough",
                "token_type": "Bearer", "scope": "auth_keys",
            }
        if url == CREATE_KEY_URL and method == "GET":
            return {"keys": [{"id": k} for k in self.entries]}
        if url.startswith(CREATE_KEY_URL + "/") and method == "GET":
            return self.entries[url[len(CREATE_KEY_URL) + 1:]]
        raise AssertionError("unexpected API operation")


def smoke(*, expires="2026-10-26T18:15:00Z", invalid=False):
    return {
        "description": "redeti-recovery-smoke", "invalid": invalid,
        "expires": expires,
        "capabilities": {"devices": {"create": {
            "reusable": False, "ephemeral": True,
            "preauthorized": False, "tags": [RECOVERY_TAG]
        }}},
    }


class InventoryTests(unittest.TestCase):
    def test_only_specific_smoke_key_counts(self):
        other = {**smoke(), "description": "regular-production-key"}
        fake = MockAPI({
            "k1TEST": smoke(),
            "k2TEST": smoke(invalid=True),
            "k3TEST": smoke(expires="2026-10-26T17:59:00Z"),
            "k4TEST": other,
            "k5TEST": {**smoke(), "expires": "BAD DATE"},
        })
        active, inactive, uncertain = inventory_smoke_keys(
            "test-id", "test-secret", transport=fake, now=NOW)
        self.assertEqual((active, inactive, uncertain), (1, 1, 2))
        self.assertTrue(all(method in ("POST", "GET") for method, _ in fake.calls))
        self.assertEqual(sum(method == "POST" for method, _ in fake.calls), 1)
        self.assertEqual(fake.calls[0][1], TOKEN_URL)

    def test_no_keys_is_zero_without_revoke(self):
        fake = MockAPI({})
        self.assertEqual(inventory_smoke_keys(
            "test-id", "test-secret", transport=fake, now=NOW), (0, 0, 0))
        self.assertEqual([method for method, _ in fake.calls],
                         ["POST", "GET"])

    def test_fails_closed_when_listing_unexpected(self):
        def invalid_api(method, url, data, headers):
            if url == TOKEN_URL:
                return {"access_token": "fake-access-token-long-enough",
                        "token_type": "Bearer", "scope": "auth_keys"}
            return {"keys": [ {"id": "../unexpected"} ]}
        with self.assertRaisesRegex(InventoryError, "unexpected_key_id"):
            inventory_smoke_keys("a", "b", transport=invalid_api, now=NOW)

    def test_key_listing_shape_codes_reveal_no_sensitive_data(self):
        # Some providers may return null, omit keys, or change the JSON
        # response format. Never interpret those cases as an empty list.
        cases = [
            ({}, "key_listing_missing_keys"),
            ({"keys": None}, "key_listing_null_keys"),
            ({"keys": {"sensitive-key-id": "sensitive-token"}},
             "key_listing_object_keys"),
            ({"keys": "sensitive-token"}, "key_listing_string_keys"),
            ({"keys": 123}, "key_listing_unexpected_keys_type"),
            ({"keys": [{"id": "test"}] * 501}, "key_listing_over_capacity"),
        ]
        for listing, expected in cases:
            with self.subTest(expected=expected):
                ops = []
                def fake(method, url, body, headers):
                    ops.append((method, url))
                    if url == TOKEN_URL:
                        return {"access_token": "fake-access-token-long-enough",
                                "token_type": "Bearer", "scope": "auth_keys"}
                    return listing
                with self.assertRaises(InventoryError) as result:
                    inventory_smoke_keys("a", "b", transport=fake, now=NOW)
                self.assertEqual(str(result.exception), expected)
                self.assertNotIn("sensitive", str(result.exception))
                self.assertEqual(ops, [("POST", TOKEN_URL),
                                       ("GET", CREATE_KEY_URL)])

    def test_null_keys_is_inconclusive_not_clean(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from services.recovery_enrollment import inspect_smoke_keys as module

        # The CLI must not claim "PASS no active keys" when the API returned
        # null; a human must review the admin Keys panel instead.
        observed = StringIO()
        with patch.object(module.os, "geteuid", return_value=0), \
             patch.object(module, "load_protected_file", return_value="test"), \
             patch.object(module, "inventory_smoke_keys",
                          side_effect=InventoryError("key_listing_null_keys")), \
             redirect_stdout(observed):
            result = module.main()
        self.assertEqual(result, 3)
        self.assertIn("INCONCLUSIVE", observed.getvalue())
        self.assertIn("do not issue a new key", observed.getvalue())
        self.assertNotIn("PASS:", observed.getvalue())

    def test_no_create_key_call_for_scope_failure(self):
        calls = []
        def fake(method, url, data, headers):
            calls.append((method, url))
            return {"access_token": "fake-access-token-long-enough",
                    "token_type": "Bearer", "scope": "devices"}
        with self.assertRaisesRegex(InventoryError, "oauth_scope_unavailable"):
            inventory_smoke_keys("a", "b", transport=fake, now=NOW)
        self.assertEqual(calls, [("POST", TOKEN_URL)])


if __name__ == "__main__":
    unittest.main()
