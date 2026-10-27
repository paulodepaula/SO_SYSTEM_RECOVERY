"""Splash regressions; no framebuffer, disks, or network are touched."""
import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "redeti_splash", ROOT / "appliance/boot/splash.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load splash module")
splash = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(splash)


class SplashTests(TestCase):
    def test_missing_framebuffer_is_non_fatal(self):
        with patch.object(splash.os, "open", side_effect=OSError("no framebuffer")):
            self.assertIsNone(splash.main())

    def test_boot_stops_splash_before_native_dashboard(self):
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        self.assertLess(
            launch.index("redeti_stop_splash"),
            launch.index("/opt/redeti-appliance/bin/redeti-ui"),
        )

    def test_technical_console_and_read_only_runtime_are_preserved(self):
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        self.assertIn("/run/redeti/ui.log", launch)
        self.assertIn("/run/redeti/ui.exit", launch)
        self.assertIn("somente leitura", launch)
        self.assertNotIn("mount ", launch)
        self.assertNotIn("fsck ", launch)


if __name__ == "__main__":
    import unittest

    unittest.main()
