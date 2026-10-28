"""Tests for the unprivileged, sanitized VPN status command."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "appliance/remote/redeti-status"
loader = importlib.machinery.SourceFileLoader("redeti_status", str(MODULE_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
status = importlib.util.module_from_spec(spec)
loader.exec_module(status)


class RedetiStatusTests(unittest.TestCase):
    def test_render_exposes_only_fixed_vpn_fields(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "vpn-status.json"
            path.write_text(json.dumps({
                "state": "connected",
                "connectivity": "connected",
                "failure_code": "none",
                "registration_stage": "registered",
                "vpn_ssh_mode": "native",
                "vpn_ip": "100.1.2.3",
                "auth_key": "tskey-auth-secret",
            }))
            output = status.render(path)
        self.assertEqual(output, [
            "vpn_state=connected",
            "connectivity=connected",
            "failure_code=none",
            "registration_stage=registered",
            "vpn_ssh_mode=native",
        ])
        self.assertNotIn("100.", "\n".join(output))
        self.assertNotIn("tskey", "\n".join(output))

    def test_missing_or_tampered_status_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "vpn-status.json"
            path.write_text('{"state":"danger","auth_key":"secret"}')
            self.assertEqual(status.render(path)[0], "vpn_state=unavailable")
            path.unlink()
            self.assertEqual(status.render(path)[0], "vpn_state=unavailable")

    def test_symlink_and_oversized_status_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            target = folder / "target"
            target.write_text('{"state":"connected"}')
            link = folder / "vpn-status.json"
            link.symlink_to(target)
            self.assertEqual(status.render(link)[0], "vpn_state=unavailable")
            link.unlink()
            target.write_text("X" * 2049)
            target.rename(link)
            self.assertEqual(status.render(link)[0], "vpn_state=unavailable")

    def test_source_and_build_install_public_command_without_socket_access(self):
        source = (ROOT / "appliance/remote/start.sh").read_text()
        lan = (ROOT / "appliance/remote/lan-start.sh").read_text()
        recipe = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        self.assertIn("/run/redeti-status", source)
        self.assertIn("chmod 0700 \"$base\"", source)
        self.assertIn("chmod 0644 \"$public_status_file.tmp\"", source)
        self.assertIn("/run/redeti-status", lan)
        self.assertNotIn("chmod 777", source + lan)
        self.assertIn("vpn_tag_failed", source)
        self.assertIn("vpn_auth_failed", source)
        self.assertIn("vpn_connectivity_failed", source)
        self.assertNotIn("tailscaled.sock", (ROOT / "appliance/remote/redeti-status").read_text())
        self.assertIn("install -m 0755 \"$root/appliance/remote/redeti-status\"", recipe)

    def test_ssh_diagnose_reads_public_status_and_early_splash_is_independent(self):
        diagnose = (ROOT / "appliance/remote/ssh-diagnose.py").read_text()
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        self.assertIn("/run/redeti-status/vpn-status.json", diagnose)
        self.assertIn("/run/redeti-status/ssh-status.json", diagnose)
        self.assertNotIn("/run/redeti/remote-status.json", diagnose)
        self.assertNotIn("redeti-early-splash.service", (ROOT / "appliance/remote/start.sh").read_text())
        self.assertIn("systemctl stop redeti-early-splash.service", launch)


if __name__ == "__main__":
    unittest.main()
