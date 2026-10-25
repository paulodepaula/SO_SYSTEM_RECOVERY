"""Static safeguards for boot service packaging (no live disks or QEMU)."""
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]

class TestBootService(unittest.TestCase):
    def test_systemd_service_runs_api_independently(self):
        unit = (BASE / "systemd/redeti-cockpit.service").read_text()
        self.assertIn("ExecStart=/usr/bin/python3 -u /opt/redeti-recovery/app/server.py --live", unit)
        self.assertIn("Restart=on-failure", unit)
        self.assertIn("WantedBy=multi-user.target", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("RuntimeDirectory=redeti", unit)

    def test_iso_recipe_contains_enabled_service(self):
        script = (BASE / "build/compose_iso.sh").read_text()
        self.assertIn('cp "$root/boot_gui/systemd/redeti-cockpit.service"', script)
        self.assertIn("multi-user.target.wants/redeti-cockpit.service", script)
        self.assertIn('ln -s ../redeti-cockpit.service', script)

    def test_firefox_does_not_own_server(self):
        script = (BASE / "build/launch.sh").read_text()
        self.assertIn("systemctl start redeti-cockpit.service", script)
        self.assertIn('target="$fallback"', script)
        self.assertIn("curl --noproxy '*'", script)
        self.assertNotIn("server_pid=", script)
        self.assertNotIn("kill \"$server_pid\"", script)

    def test_offline_page_can_be_shown_without_server(self):
        html = (BASE / "ui/offline.html").read_text()
        self.assertIn("serviço local de diagnóstico", html)
        self.assertIn("redeti-cockpit.service", html)

if __name__ == "__main__":
    unittest.main()
