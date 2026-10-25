"""Review native appliance boot recipe without touching any attached disk."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ApplianceBuildSafetyTests(unittest.TestCase):
    def test_recipe_disables_graphical_desktop(self):
        cfg = (ROOT / "appliance/boot/900-redeti-appliance.yaml").read_text()
        self.assertIn("dostartx: false", cfg)
        self.assertIn("loadsrm: true", cfg)
        self.assertIn("autorun:", cfg)
        self.assertIn("/opt/redeti-appliance/launch.sh", cfg)
        self.assertNotIn("gui_autostart", cfg)

    def test_appliance_does_not_use_legacy_web(self):
        iso = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        self.assertNotIn("boot_gui", iso)
        self.assertNotIn("firefox", launch.lower())
        self.assertNotIn("startx", launch.lower())
        self.assertNotIn("http://", launch)
        self.assertIn("redeti-ui", iso + launch)

    def test_compiler_does_not_mount_host_disks(self):
        native = (ROOT / "appliance/build/build-native-arch.sh").read_text()
        self.assertIn(":/project:ro", native)
        self.assertNotIn("--privileged", native)
        self.assertNotIn("/dev/sd", native)
        self.assertNotIn("dd if=", native)

    def test_build_preserves_older_iso_until_qemu_approval(self):
        script = (ROOT / "appliance/build/build-local.sh").read_text()
        self.assertIn("sha256sum", script)
        self.assertNotIn("prune-recovery-isos.sh", script)

    def test_shell_scripts_have_valid_syntax(self):
        for name in ("appliance/build/build-native-arch.sh", "appliance/build/compose-appliance.sh",
                     "appliance/build/build-local.sh", "appliance/boot/launch.sh"):
            process = subprocess.run(["bash", "-n", str(ROOT / name)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, f"{name}: {process.stderr}")


if __name__ == "__main__":
    unittest.main()
