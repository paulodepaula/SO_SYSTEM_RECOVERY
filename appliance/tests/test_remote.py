"""Remote access safety: fake lsblk and static source checks only."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("remote_provision", ROOT / "appliance/remote/provision.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RemoteBootstrapTests(unittest.TestCase):
    def test_only_explicit_usb_volume(self):
        devices = [
            {"name": "/dev/sda", "type": "disk", "tran": "sata", "rm": False,
             "children": [{"name": "/dev/sda1", "type": "part", "label": "REDETI_CFG", "fstype": "vfat"}]},
            {"name": "/dev/sdb", "type": "disk", "tran": "usb", "rm": True,
             "children": [{"name": "/dev/sdb1", "type": "part", "label": "Ventoy", "fstype": "exfat"}]},
        ]
        self.assertEqual(module.candidates(devices), ["/dev/sdb1"])

    def test_generic_ntfs_disks_never_provisioned(self):
        devices = [{"name": "/dev/sda", "type": "disk", "tran": "sata", "rm": False,
                    "children": [{"name": "/dev/sda1", "type": "part",
                                  "label": "Ventoy", "fstype": "ntfs"}]}]
        self.assertEqual(module.candidates(devices), [])

    def test_ambiguous_usb_sources_are_not_accepted(self):
        devices = [{"name": "/dev/sdb", "type": "disk", "tran": "usb", "rm": True,
                    "children": [
                        {"name": "/dev/sdb1", "type": "part", "label": "Ventoy", "fstype": "exfat"},
                        {"name": "/dev/sdb2", "type": "part", "label": "REDETI_CFG", "fstype": "vfat"},
                    ]}]
        self.assertEqual(len(module.candidates(devices)), 2)

    def test_tailscale_ssh_uses_paulo(self):
        code = (ROOT / "appliance/remote/start.sh").read_text()
        self.assertIn("useradd --create-home --user-group", code)
        self.assertIn("usermod --password '*' paulo", code)
        self.assertNotIn("systemctl mask --runtime --now sshd.service", code)
        self.assertIn('--ssh="$ssh_managed" --hostname=', code)
        self.assertIn('ssh_managed=false',code)
        self.assertIn('vpn_ssh_mode="disabled"',code)
        self.assertIn('vpn_ssh_mode="managed"',code)
        self.assertIn('tailscale-ssh.enable',code)
        self.assertIn('[ "$(wc -c < "$marker")" -eq 0 ]',code)
        self.assertIn('[ ! -L "$marker" ]',code)
        self.assertNotIn('--ssh --hostname=', code)
        self.assertIn('--netfilter-mode=off',code)
        self.assertIn('findmnt -n -o FSTYPE -T "$base"',code)
        self.assertIn('status "unsafe_runtime_storage"',code)
        self.assertNotIn('iptables -F REDETI_VPN_INPUT',code)
        self.assertIn('status "invalid_auth_key"',code)
        self.assertIn('"$provision_script" sources',code)
        self.assertIn('mount -o ro,nosuid,nodev,noexec',code)
        self.assertIn('findmnt -r -n -S "$source"',code)
        self.assertIn('REDETI_VPN_INPUT',code)
        self.assertIn('iptables -I INPUT 1 -i tailscale0',code)
        self.assertIn('iptables -I OUTPUT 1 -o tailscale0 -m conntrack --ctstate NEW -j DROP',code)
        self.assertIn('iptables -A REDETI_VPN_INPUT -j DROP',code)
        self.assertIn('iptables -I REDETI_VPN_INPUT 2 -d "$ip/32" -p tcp --dport 22 -j ACCEPT',code)
        self.assertIn('trap cleanup EXIT',code)
        self.assertIn("--advertise-tags=tag:redeti-recovery", code)
        self.assertIn("useradd --create-home --user-group", code)
        self.assertIn('iptables -I INPUT 1 -i tailscale0', code)
        self.assertIn('-d "$ip/32" -p tcp --dport 22 -j ACCEPT', code)
        self.assertIn('status "firewall_blocked"', code)
        self.assertNotIn('iptables -P INPUT ACCEPT', code)
        self.assertNotIn('iptables -F INPUT', code)
        self.assertNotIn('iptables -F OUTPUT', code)
        self.assertIn("--state=mem:", code)
        self.assertIn('ssh_user":"paulo', code)
        self.assertIn('"vpn_ssh_mode":"%s"', code)
        self.assertIn("--auth-key=\"file:", code)
        self.assertNotIn("PasswordAuthentication yes", code)
        self.assertNotIn("PermitRootLogin yes", code)

    def test_vpn_does_not_embed_secrets_or_publish_services(self):
        vpn=(ROOT/"appliance/remote/start.sh").read_text()
        sshd=(ROOT/"appliance/remote/sshd_config").read_text()
        iso=(ROOT/"appliance/build/compose-appliance.sh").read_text()
        self.assertIn('tskey-auth-',vpn)
        self.assertIn('--auth-key="file:$auth_file"',vpn)
        self.assertNotIn('--auth-key=tskey-',vpn)
        self.assertIn('--state=mem:',vpn)
        self.assertIn('rm -f -- "$auth_file"',vpn)
        self.assertIn('--accept-routes=false --accept-dns=false',vpn)
        for forbidden in ('--advertise-routes=', '--advertise-exit-node',
                          '--ssh --hostname=', 'tailscale serve', 'tailscale funnel',
                          'iptables -P INPUT ACCEPT', 'iptables -F INPUT',
                          'blockdev --setrw', 'dmsetup create'):
            self.assertNotIn(forbidden,vpn)
        for expected in ('AllowUsers paulo','PasswordAuthentication no',
                         'AuthenticationMethods publickey','PermitRootLogin no',
                         'AllowTcpForwarding no'):
            self.assertIn(expected,sshd)
        self.assertNotIn('ts-authkey"',iso)
        self.assertIn('Tailscale binaries and remote scripts',iso)

    def test_no_disk_mounting_without_usb_validation(self):
        code = (ROOT / "appliance/remote/start.sh").read_text()
        self.assertIn("remote/provision.py", code)
        self.assertIn("ro,nosuid,nodev,noexec", code)
        self.assertIn("/REDETI/ts-authkey", code)
        self.assertIn('rm -f -- "$auth_file"', code)

    def test_recipe_includes_vpn_payload_no_secret(self):
        script = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        self.assertIn('remote/start.sh', script)
        self.assertIn('remote/provision.py', script)
        self.assertIn('"$tsout/$name"', script)
        self.assertIn('sshd.service', script)
        self.assertNotIn('ts-authkey"', script)

    def test_gui_remains_independent(self):
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        self.assertIn("--unit=redeti-remote", launch)
        self.assertIn("|| true", launch)
        self.assertIn("redeti-ui", launch)
        gui = (ROOT / "appliance/native/ui/dashboard.c").read_text()
        self.assertIn('paulo@%s', gui)
        self.assertIn('remote-status.json', gui)

    def test_remote_scripts_shell_syntax(self):
        for name in ("appliance/remote/start.sh", "appliance/build/fetch-tailscale.sh"):
            result = subprocess.run(["bash", "-n", str(ROOT / name)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == "__main__":
    unittest.main()
