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

    def test_only_tailscale_ssh_is_enabled(self):
        code = (ROOT / "appliance/remote/start.sh").read_text()
        self.assertIn("useradd --create-home --user-group", code)
        self.assertIn("passwd -l redeti", code)
        self.assertIn("systemctl mask --runtime --now sshd.service", code)
        self.assertIn("--ssh --hostname", code)
        self.assertIn("--advertise-tags=tag:redeti-recovery", code)
        self.assertIn("sshd.socket", code)
        self.assertIn("--state=mem:", code)
        self.assertIn("--auth-key=\"file:", code)
        self.assertNotIn("PasswordAuthentication yes", code)
        self.assertNotIn("PermitRootLogin yes", code)

    def test_no_disk_mounting_without_usb_validation(self):
        code = (ROOT / "appliance/remote/start.sh").read_text()
        self.assertIn("remote/provision.py", code)
        self.assertIn("ro,nosuid,nodev,noexec", code)
        self.assertIn("/REDETI/ts-authkey", code)
        self.assertIn('rm -f "$base/ts-authkey"', code)

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
        gui = (ROOT / "appliance/native/main.c").read_text()
        self.assertIn('redeti@%s', gui)
        self.assertIn('remote-status.json', gui)

    def test_remote_scripts_shell_syntax(self):
        for name in ("appliance/remote/start.sh", "appliance/build/fetch-tailscale.sh"):
            result = subprocess.run(["bash", "-n", str(ROOT / name)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == "__main__":
    unittest.main()
