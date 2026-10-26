"""SSH diagnosis tests; no customer disks or real network access."""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "ssh_diagnose", ROOT / "appliance/remote/ssh-diagnose.py"
)
diagnose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnose)


class _FakeSocket:
    def __init__(self, reply: bytes):
        self.reply = reply
        self.timeout = None
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def settimeout(self, timeout):
        self.timeout = timeout
    def recv(self, limit):
        return self.reply


class SSHDiagnosisTests(TestCase):
    def test_only_local_port_22_is_probed(self):
        calls = []
        def connect(addr, timeout):
            calls.append(addr)
            return _FakeSocket(b"SSH-2.0-OpenSSH_mock\r\n")
        with patch.object(diagnose.socket, "create_connection", side_effect=connect):
            self.assertEqual(diagnose._local_banner_probe(),
                             "ssh_identification_ok")
        self.assertEqual(calls, [("127.0.0.1", 22)])

    def test_local_timeout_has_safe_fixed_code(self):
        with patch.object(
            diagnose.socket, "create_connection", side_effect=socket.timeout
        ):
            self.assertEqual(diagnose._local_banner_probe(), "identification_timeout")

    def test_vpn_state_and_mode_allowlisted(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "status.json"
            p.write_text(json.dumps({
                "state": "connected", "vpn_ssh_mode": "managed",
                "vpn_ip": "100.1.2.3", "token": "SHOULD-NOT-APPEAR",
            }))
            self.assertEqual(diagnose._status(
                p, key="state", allow=diagnose._VPN_STATES), "connected")
            self.assertEqual(diagnose._ssh_mode(p), "managed")
            p.write_text('{"state":"danger\nRAW","vpn_ssh_mode":"unsafe"}')
            self.assertEqual(diagnose._status(
                p, key="state", allow=diagnose._VPN_STATES), "unavailable")
            self.assertEqual(diagnose._ssh_mode(p), "unknown")

    def test_symlinks_and_oversized_status_are_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            target = folder / "target"
            target.write_text('{"state":"connected","vpn_ssh_mode":"managed"}')
            symlink = folder / "link"
            symlink.symlink_to(target)
            self.assertEqual(diagnose._ssh_mode(symlink), "unknown")
            self.assertEqual(diagnose._status(
                symlink, key="state", allow=diagnose._VPN_STATES), "unavailable")
            target.write_text("X" * 2049)
            self.assertEqual(diagnose._ssh_mode(target), "unknown")

    def test_firewall_checks_only_read_commands(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if args[-1] == "REDETI_VPN_INPUT":
                return subprocess.CompletedProcess(args, 0,
                    "-A REDETI_VPN_INPUT -p tcp -m tcp --dport 22 -j ACCEPT\n"
                    "-A REDETI_VPN_INPUT -j DROP\n", "")
            return subprocess.CompletedProcess(args, 0,
                    "-A INPUT -i tailscale0 -j REDETI_VPN_INPUT\n", "")
        with patch.object(diagnose.subprocess, "run", side_effect=run):
            self.assertEqual(diagnose._firewall(), "vpn_ssh_rule_present")
        self.assertEqual(calls, [
            ["iptables", "-S", "REDETI_VPN_INPUT"],
            ["iptables", "-S", "INPUT"],
        ])

    def test_missing_vpn_allow_rule_returns_missing(self):
        def run(args, **kwargs):
            return subprocess.CompletedProcess(args, 0,
                "-A INPUT -j DROP\n" if args[-1] == "INPUT" else
                "-A REDETI_VPN_INPUT -j DROP\n", "")
        with patch.object(diagnose.subprocess, "run", side_effect=run):
            self.assertEqual(diagnose._firewall(), "vpn_ssh_rule_missing")

    def test_cli_has_fixed_output_and_no_credential_leaks(self):
        fake = {
            "vpn_state": "connected",
            "vpn_ssh_mode": "native",
            "lan_ssh_state": "ready",
            "sshd_port_22_listening": "yes",
            "local_ssh_identification": "ssh_identification_ok",
            "vpn_firewall": "vpn_ssh_rule_present",
            "native_ssh_banner": "present",
        }
        from io import StringIO
        from contextlib import redirect_stdout
        self.assertEqual(diagnose.main([]), 2)
        buf = StringIO()
        with patch.object(diagnose, "diagnose", return_value=fake):
            with redirect_stdout(buf):
                self.assertEqual(diagnose.main(["--read-only"]), 0)
        out = buf.getvalue()
        self.assertIn("diagnostic_complete=read_only", out)
        self.assertNotIn("tskey", out)
        self.assertNotIn("100.", out)

    def test_future_iso_bundles_read_only_diagnostic(self):
        recipe = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        self.assertIn("remote/ssh-diagnose.py", recipe)
        self.assertIn('install -m 0755 "$root/appliance/remote/ssh-diagnose.py"', recipe)
        self.assertNotIn('authkey', (ROOT / "appliance/remote/ssh-diagnose.py").read_text().lower())

    def test_no_mutating_iptables_or_disks_in_source(self):
        code = (ROOT / "appliance/remote/ssh-diagnose.py").read_text()
        self.assertNotIn('["iptables", "-I"', code)
        self.assertNotIn('["iptables", "-A"', code)
        self.assertNotIn('["iptables", "-F"', code)
        self.assertNotIn('tailscale up', code)
        self.assertNotIn('ssh-keygen ', code)


if __name__ == "__main__":
    import unittest
    unittest.main()
