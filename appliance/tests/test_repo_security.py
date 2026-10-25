"""Fail CI if credential-like material or customer disk images are tracked.

This is defense-in-depth: repository review and short-lived tokens are still
required. Do not print matched secrets to CI logs.
"""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

SECRET_NAMES = (
    "authorized_keys", "ts-authkey", ".p12", ".pfx", ".ppk",
    "tailscaled.state", "tailscale.state", ".qcow2", ".vmdk",
)
CONTENT_PATTERNS = (
    re.compile(rb"-----BEGIN (?:OPENSSH|RSA|EC|DSA|ENCRYPTED) PRIVATE KEY-----"),
    re.compile(rb"tskey-auth-[A-Za-z0-9_-]{25,}"),
    re.compile(rb"-----BEGIN " + rb"PGP PRIVATE KEY BLOCK-----"),
)


class RepositorySecurityTests(unittest.TestCase):
    def test_gitignore_blocks_private_device_credentials(self):
        data = (ROOT / ".gitignore").read_text()
        for value in ("**/ts-authkey", "**/authorized_keys",
                      "**/*_ed25519", "**/*.ppk", "**/*.pfx", "**/*.qcow2"):
            self.assertIn(value, data)

    def test_no_live_secrets_or_customer_disks_tracked(self):
        result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                                capture_output=True, check=True)
        tracked = [Path(x.decode("utf-8", errors="replace"))
                   for x in result.stdout.split(b"\0") if x]
        for path in tracked:
            name = path.name.lower()
            self.assertFalse(
                name in SECRET_NAMES or any(name.endswith(s) for s in
                (".ppk", ".p12", ".pfx", ".qcow2", ".vmdk")),
                "Suspicious tracked filename (contents not shown): " + name)
            if path.suffix.lower() not in (
                ".py", ".sh", ".c", ".h", ".md", ".txt", ".yml",
                ".yaml", ".json", ".toml", ".conf", ".html", ".css",
            ):
                continue
            file = ROOT / path
            if not file.is_file() or file.stat().st_size > 2_000_000:
                continue
            payload = file.read_bytes()
            for pattern in CONTENT_PATTERNS:
                self.assertFalse(
                    pattern.search(payload) is not None,
                    "Credential-like content in tracked file: " + str(path))
