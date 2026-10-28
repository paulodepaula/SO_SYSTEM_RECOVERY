"""Recovery OS LAN-SSH tests. No network, disks, or SSH services touched."""
import base64
import importlib.util
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("appliance_lan", ROOT / "appliance/remote/lan.py")
lan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lan)


def example_key():
    wire = b"\x00\x00\x00\x0bssh-ed25519" + b"\x00\x00\x00\x20" + bytes(range(32))
    return b"ssh-ed25519 " + base64.b64encode(wire) + b" test-key\n"


class LanSSHTests(unittest.TestCase):
    def test_allow_only_directly_attached_private_subnets(self):
        interfaces = [
            {"ifname": "enp0s3", "operstate": "UP", "addr_info": [
                {"family": "inet", "scope": "global", "local": "192.168.10.45", "prefixlen": 24}]},
            {"ifname": "tailscale0", "operstate": "UP", "addr_info": [
                {"family": "inet", "scope": "global", "local": "100.100.100.10", "prefixlen": 32}]},
            {"ifname": "eth0", "operstate": "UP", "addr_info": [
                {"family": "inet", "scope": "global", "local": "8.8.8.8", "prefixlen": 24}]},
            {"ifname": "docker0", "operstate": "UP", "addr_info": [
                {"family": "inet", "scope": "global", "local": "172.17.0.1", "prefixlen": 16}]},
        ]
        self.assertEqual(lan.local_networks(interfaces), [(
            "enp0s3", "192.168.10.0/24", "192.168.10.45")])

    def test_qemu_nat_private_network_is_allowed(self):
        interfaces = [{"ifname": "enp0s3", "operstate": "UP", "addr_info": [
            {"family": "inet", "scope": "global", "local": "10.0.2.15", "prefixlen": 24}]}]
        self.assertEqual(lan.local_networks(interfaces)[0][1], "10.0.2.0/24")

    def test_no_broad_untrusted_lan_network(self):
        interfaces = [{"ifname": "eth0", "operstate": "UP", "addr_info": [
            {"family": "inet", "scope": "global", "local": "10.12.20.3", "prefixlen": 7}]}]
        self.assertEqual(lan.local_networks(interfaces), [])

    def test_accept_ed25519_key_without_authorized_options(self):
        self.assertTrue(lan.valid_keys(example_key()).startswith(b"ssh-ed25519 "))
        self.assertNotIn(b"test-key", lan.valid_keys(example_key()))

    def test_accept_two_distinct_ed25519_keys(self):
        wire = b"\x00\x00\x00\x0bssh-ed25519" + b"\x00\x00\x00\x20" + bytes(range(31, -1, -1))
        second = b"ssh-ed25519 " + base64.b64encode(wire) + b" second-key\n"
        validated = lan.valid_keys(example_key() + second)
        self.assertEqual(validated.count(b"\n"), 2)
        self.assertNotIn(b"test-key", validated)
        self.assertNotIn(b"second-key", validated)

    def test_reject_key_options_and_password_material(self):
        for bad in (b"command=\"id\" " + example_key(),
                    b"ssh-rsa AAAA\n", b"private-key\n",
                    b"", b"ssh-ed25519 $$$$\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    lan.valid_keys(bad)

    def test_config_does_not_permit_root_or_passwords(self):
        config = (ROOT / "appliance/remote/sshd_config").read_text()
        for expected in ("AllowUsers paulo", "PasswordAuthentication no",
                         "KbdInteractiveAuthentication no", "PermitRootLogin no",
                         "AuthenticationMethods publickey", "AddressFamily inet"):
            self.assertIn(expected, config)
        self.assertNotIn("AllowUsers root", config)

    def test_isolated_boot_and_explicit_firewall(self):
        script = (ROOT / "appliance/remote/lan-start.sh").read_text()
        self.assertIn("useradd --create-home", script)
        self.assertIn("REDETI_LAN_SSH", script)
        self.assertIn('iptables -I INPUT 1 -p tcp --dport 22 -j REDETI_LAN_SSH', script)
        self.assertIn('iptables -I REDETI_LAN_SSH 1 -i "$iface" -s "$subnet"', script)
        self.assertIn("ro,nosuid,nodev,noexec", script)
        self.assertIn("ssh_host_ed25519_key", script)
        self.assertNotIn("iptables -P INPUT ACCEPT", script)
        self.assertNotIn("iptables -F INPUT", script)
        self.assertNotIn("PermitRootLogin yes", script)
        self.assertEqual(subprocess.run(["bash", "-n", str(ROOT / "appliance/remote/lan-start.sh")],
                                        capture_output=True).returncode, 0)

    def test_lan_sshd_start_does_not_block_usb_key_provisioning(self):
        script = (ROOT / "appliance/remote/lan-start.sh").read_text()
        self.assertIn("--no-block", script)
        self.assertLess(script.index("--no-block"), script.index("key_loaded=false"))

    def test_ssh_usb_provisioning_reasons_are_safe_and_specific(self):
        script=(ROOT / "appliance/remote/lan-start.sh").read_text()
        self.assertIn('"key_reason":"%s"',script)
        for reason in ("waiting_usb","usb_mount_failed","key_file_missing",
                       "invalid_public_key","installed"):
            self.assertIn(f'key_reason="{reason}"',script)
        self.assertIn('status "awaiting_key" "$primary_ip" "$key_reason"',script)
        self.assertIn('classify_mount_error()',script)
        self.assertIn('key_reason="usb_device_busy"',script)
        self.assertIn('key_reason="usb_filesystem_error"',script)
        self.assertIn('mount -o ro,nosuid,nodev,noexec',script)
        self.assertIn('mount -o ro,nosuid,nodev,noexec',script)
        self.assertIn('umount -- "$mountpoint"',script)
        self.assertNotIn('PasswordAuthentication yes',script)
        self.assertNotIn('PermitRootLogin yes',script)

    def test_banner_is_packaged_and_contains_no_secrets(self):
        config = (ROOT / "appliance/remote/sshd_config").read_text()
        builder = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        banner = (ROOT / "appliance/remote/ssh-banner.txt").read_text()
        self.assertIn("Banner /opt/redeti-appliance/remote/ssh-banner.txt", config)
        self.assertIn('remote/ssh-banner.txt', builder)
        self.assertIn("REDETI RECOVERY OS", banner)
        self.assertIn("Acesso restrito", banner)
        self.assertNotIn("100.", banner)
        self.assertNotIn("tskey-", banner)
        self.assertNotIn("PRIVATE KEY", banner)

    def test_boot_and_image_include_lan_ssh(self):
        launcher = (ROOT / "appliance/boot/launch.sh").read_text()
        iso = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        gui = (ROOT / "appliance/native/ui/dashboard.c").read_text()
        self.assertIn("redeti-lan-ssh", launcher)
        for name in ("lan-start.sh", "lan.py", "sshd_config"):
            self.assertIn(name, iso)
        self.assertIn("paulo@%s", gui)
        self.assertIn("s_ssh", gui)

if __name__ == "__main__":
    unittest.main()
