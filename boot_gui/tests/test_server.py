"""Unit checks: no physical hardware accessed."""
from pathlib import Path
import importlib.util
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "app" / "server.py"
spec = importlib.util.spec_from_file_location("redeti_boot_gui", SOURCE)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class BootGuiTest(unittest.TestCase):
    def test_cpu_model(self):
        self.assertEqual(app.cpu("model name : Intel Test CPU\n"), "Intel Test CPU")

    def test_windows_disk_is_not_confirmed_boot(self):
        disks, target = app.disks_from([{
            "name":"/dev/sda","type":"disk","model":"LAB","tran":"ata","rm":False,
            "size":512110190592,"children":[{"name":"/dev/sda1","type":"part","fstype":"ntfs"}]
        }])
        self.assertEqual(target["status"], "PROVAVEL")
        self.assertIn("ainda não comprovado", target["note"])

    def test_ventoy_not_selected(self):
        _, target = app.disks_from([{"name":"/dev/sdb","type":"disk","tran":"usb","rm":True}])
        self.assertEqual(target["status"], "NAO_IDENTIFICADO")

    def test_multiple_disks_require_selection(self):
        _, target = app.disks_from([
            {"name":"/dev/sda","type":"disk","tran":"ata","rm":False},
            {"name":"/dev/sdc","type":"disk","tran":"ata","rm":False},
        ])
        self.assertEqual(target["status"], "SELECAO_NECESSARIA")

    def test_demo_has_no_hardware_calls(self):
        def forbidden(_args):
            self.fail("Demo must not probe any disk")
        result=app.overview(live=False,command=forbidden,files=lambda _: "",efi=False,logical=1)
        self.assertEqual(result["mode"], "DEMO")
        self.assertFalse(result["repair_allowed"])

    def test_smart_blocks_multiple_drives(self):
        def mocked(_args):
            return (0,'{"blockdevices":[{"name":"/dev/sda","type":"disk","tran":"ata","rm":false},{"name":"/dev/sdc","type":"disk","tran":"ata","rm":false}]}',"")
        self.assertEqual(app.smart(live=True,command=mocked)["status"], "BLOCKED")

    def test_no_write_commands(self):
        with self.assertRaises(ValueError):
            app.run(["mount","/dev/sda1","/mnt"])

if __name__=="__main__":
    unittest.main()
