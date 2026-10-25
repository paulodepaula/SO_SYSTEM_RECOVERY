import json
import unittest
from appliance.probe import LSBLK, collect


def fake_reader(path):
    return {"/proc/cpuinfo": "model name : CPU TEST 64-bit\n",
            "/proc/meminfo": "MemTotal:       3145728 kB\n"}.get(path, "")


def runner_with(disks):
    def runner(cmd):
        assert cmd == LSBLK
        return 0, json.dumps({"blockdevices": disks}), ""
    return runner


class ApplianceProbeTests(unittest.TestCase):
    def test_detects_firmware_cpu_and_ram(self):
        r = collect(runner_with([]), fake_reader, efi_present=True, logical_cpus=4)
        self.assertEqual(r["cpu"], {"model": "CPU TEST 64-bit", "logical_processors": 4})
        self.assertEqual(r["ram_bytes"], 3221225472)
        self.assertEqual(r["recovery_boot_firmware"], "UEFI")
        self.assertEqual(r["windows_boot_firmware"], "NOT_VERIFIED")

    def test_empty_disks_not_crash(self):
        r = collect(runner_with([]), fake_reader, efi_present=False)
        self.assertEqual(r["target"]["status"], "NO_INTERNAL_DISK")

    def test_windows_candidate_not_confirmed(self):
        r = collect(runner_with([{
            "name": "/dev/sda", "type": "disk", "tran": "ata", "rm": False,
            "children": [{"name": "/dev/sda1", "type": "part", "fstype": "ntfs"}]}]),
            fake_reader, efi_present=False)
        self.assertEqual(r["target"]["status"], "WINDOWS_CANDIDATE")
        self.assertEqual(r["operating_system_confirmation"], "NOT_TESTED")

    def test_usb_ventoy_cannot_be_internal_candidate(self):
        r = collect(runner_with([{
            "name": "/dev/sdb", "type": "disk", "tran": "usb", "rm": True,
            "children": [{"name": "/dev/sdb1", "type": "part", "fstype": "ntfs"}]}]),
            fake_reader, efi_present=False)
        self.assertEqual(r["target"]["status"], "NO_INTERNAL_DISK")

    def test_multiple_internal_disks_requires_selection(self):
        r = collect(runner_with([
            {"name": "/dev/sda", "type": "disk", "tran": "ata", "rm": False},
            {"name": "/dev/nvme0n1", "type": "disk", "tran": "nvme", "rm": False},
        ]), fake_reader, efi_present=False)
        self.assertEqual(r["target"]["status"], "MULTIPLE_INTERNAL_DISKS")

    def test_bad_lsblk_data_still_safe(self):
        r = collect(lambda cmd: (0, "broken json", ""), fake_reader, efi_present=False)
        self.assertTrue(r["warnings"])
        self.assertFalse(r["writes_to_disks"])
        self.assertFalse(r["mounts_performed"])


if __name__ == "__main__":
    unittest.main()
