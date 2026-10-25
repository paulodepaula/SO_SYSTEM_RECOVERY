"""Read-only Ventoy provisioning fallback tests; no real block devices accessed."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "redeti_ventoy_provision", ROOT / "appliance/remote/provision.py")
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


def inventory(label="Ventoy", fs="exfat"):
    return [{"name": "/dev/sda", "type": "disk", "tran": "sata", "rm": False,
             "children": [{"name": "/dev/sda1", "type": "part",
                           "label": "Ventoy", "fstype": "exfat"}]},
            {"name": "/dev/sdb", "type": "disk", "tran": "usb", "rm": True,
             "children": [{"name": "/dev/sdb1", "type": "part",
                           "label": label, "fstype": fs}]}]


class VentoyFallbackTests(TestCase):
    def test_mapper_is_accepted_only_for_same_usb_partition(self):
        with TemporaryDirectory() as root:
            path = Path(root)
            dev, sys = path / "dev", path / "sys"
            (dev / "mapper").mkdir(parents=True)
            (sys / "class/block/dm-1/slaves").mkdir(parents=True)
            (dev / "sdb1").touch()
            (dev / "dm-1").touch()
            (dev / "mapper/VentoyPart").symlink_to("../dm-1")
            (sys / "class/block/dm-1/slaves/sdb1").touch()
            with mock.patch.object(provision.stat, "S_ISBLK", return_value=True):
                self.assertEqual(
                    provision.verified_ventoy_mapper("/dev/sdb1", dev, sys),
                    str(dev / "mapper/VentoyPart"))
                self.assertEqual(
                    provision.sources(inventory(), dev, sys),
                    ["/dev/sdb1", str(dev / "mapper/VentoyPart")])
                # Refuse mapper backed by a customer's disk.
                self.assertIsNone(
                    provision.verified_ventoy_mapper("/dev/sda1", dev, sys))
                (sys / "class/block/dm-1/slaves/sda1").touch()
                self.assertIsNone(
                    provision.verified_ventoy_mapper("/dev/sdb1", dev, sys))

    def test_older_ventoy_exposes_partition_named_mapper(self):
        # Ventoy installed before release 1.1.18 can use /dev/mapper/sdb1.
        with TemporaryDirectory() as root:
            path = Path(root)
            dev, sys = path / "dev", path / "sys"
            (dev / "mapper").mkdir(parents=True)
            (sys / "class/block/dm-2/slaves").mkdir(parents=True)
            (dev / "sdb1").touch()
            (dev / "sda1").touch()
            (dev / "dm-2").touch()
            (dev / "mapper/sdb1").symlink_to("../dm-2")
            (sys / "class/block/dm-2/slaves/sdb1").touch()
            with mock.patch.object(provision.stat, "S_ISBLK", return_value=True):
                self.assertEqual(
                    provision.sources(inventory(), dev, sys),
                    ["/dev/sdb1", str(dev / "mapper/sdb1")])
                self.assertEqual(
                    provision.verified_ventoy_mapper("/dev/sdb1",dev,sys),
                    str(dev / "mapper/sdb1"))
                # Same filename without matching hardware must not pass.
                (sys / "class/block/dm-2/slaves/sdb1").unlink()
                (sys / "class/block/dm-2/slaves/sda1").touch()
                self.assertEqual(provision.sources(inventory(),dev,sys),
                                 ["/dev/sdb1"])

    def test_missing_mapper_does_not_get_created(self):
        with TemporaryDirectory() as root:
            path = Path(root)
            self.assertEqual(
                provision.sources(inventory(), path / "dev", path / "sys"),
                ["/dev/sdb1"])
            self.assertFalse((path / "dev/mapper/VentoyPart").exists())

    def test_no_fallback_for_other_labels_or_unsupported_fs(self):
        with TemporaryDirectory() as root:
            path = Path(root)
            self.assertEqual(
                provision.sources(inventory("REDETI_CFG", "vfat"),
                                  path / "dev", path / "sys"),
                ["/dev/sdb1"])
            self.assertEqual(
                provision.sources(inventory("Ventoy", "ntfs"),
                                  path / "dev", path / "sys"), [])

    def test_never_choose_ambiguous_usb_partition(self):
        devices = inventory()
        devices[-1]["children"].append(
            {"name": "/dev/sdb2", "type": "part",
             "label": "REDETI_CFG", "fstype": "vfat"})
        self.assertEqual(provision.sources(devices), [])

    def test_script_keeps_mount_read_only_and_does_not_unmount_system_mount(self):
        code = (ROOT / "appliance/remote/lan-start.sh").read_text()
        self.assertIn('python3 "$ROOT/provision.py" sources', code)
        self.assertIn('findmnt -r -n -S "$source" -o TARGET', code)
        self.assertIn('mount -o ro,nosuid,nodev,noexec -- "$source"', code)
        self.assertIn('if [ "$mounted_here" = true ]; then', code)
        self.assertIn('umount -- "$mountpoint"', code)
        self.assertIn('[ ! -L "$keyroot/REDETI" ]', code)
        self.assertNotIn("dmsetup create", code)
        self.assertNotIn("blockdev --setrw", code)
        self.assertNotIn("PasswordAuthentication yes", code)
