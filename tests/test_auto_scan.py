"""No hardware/disk changes: simulated backends for the automatic scanner."""
import json
from recovery.auto_scan import scan, parse_smart, file_evidence

def inventory():
    return {"blockdevices": [
        {"name": "/dev/nvme0n1", "type": "disk", "size": 512000000000,
         "model": "LAB", "pttype": "gpt", "rm": False, "tran": "nvme",
         "children": [
             {"name": "/dev/nvme0n1p1", "type": "part", "fstype": "ntfs", "mountpoints": [None]},
             {"name": "/dev/nvme0n1p2", "type": "part", "fstype": "ntfs", "mountpoints": ["/mnt/rw"]},
             {"name": "/dev/nvme0n1p3", "type": "part", "fstype": "vfat",
              "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b", "mountpoints": [None]}
         ]},
        {"name": "/dev/sdb", "type": "disk", "size": 64000000000,
         "tran": "usb", "rm": True,
         "children": [{"name": "/dev/sdb1", "type": "part", "fstype": "exfat", "mountpoints": [None]}]}
    ]}

def mock_runner(smart="PASSED", mount_failure=False):
    calls = []
    last_source = ["/dev/nvme0n1p1"]
    def run(args):
        calls.append(args)
        if args[0] == "smartctl":
            return 0, f"SMART overall-health self-assessment test result: {smart}\n", ""
        if args[0] == "mount":
            last_source[0] = args[-2]
            return (1 if mount_failure else 0), "", ("mock fail" if mount_failure else "")
        if args[0] == "umount":
            return 0, "", ""
        if args[0] == "findmnt":
            if "--json" in args:
                target = args[args.index("--mountpoint") + 1]
                return 0, json.dumps({"filesystems": [{
                    "source": last_source[0], "target": target,
                    "fstype": "vfat" if last_source[0].endswith("p3") else "fuseblk",
                    "options": "ro,nosuid"
                }]}), ""
            return 1, "", ""
        raise AssertionError(args)
    return run, calls

def test_usb_protection_and_ro_mounts(tmp_path):
    run, calls = mock_runner()
    report = scan(inventory(), run, tmp_path)
    assert report["disks"][1]["reason"] == "USB_OR_REMOVABLE_PROTECTED"
    assert not any("/dev/sdb" in " ".join(c) for c in calls)
    assert any(c[0] == "umount" for c in calls)
    assert all("ro," in " ".join(c) for c in calls if c[0] == "mount")
    assert not list(tmp_path.iterdir())

def test_rw_mounted_volume_skipped(tmp_path):
    run, calls = mock_runner()
    report = scan(inventory(), run, tmp_path)
    assert report["disks"][0]["volumes"][1]["result"] == "ALREADY_MOUNTED_SKIPPED"
    assert "/dev/nvme0n1p2" not in " ".join(" ".join(c) for c in calls)

def test_failed_smart_blocks_mount(tmp_path):
    run, calls = mock_runner("FAILED")
    report = scan(inventory(), run, tmp_path)
    assert report["disks"][0]["reason"] == "STORAGE_RISK_NO_FURTHER_SCAN"
    assert not any(c[0] == "mount" for c in calls)

def test_inconclusive_smart_blocks_mount(tmp_path):
    run, calls = mock_runner("not supported")
    report = scan(inventory(), run, tmp_path)
    assert report["disks"][0]["reason"] == "SMART_INCONCLUSIVE_NO_MOUNT"
    assert not any(c[0] == "mount" for c in calls)

def test_not_tested_integrity_is_explicit(tmp_path):
    run, calls = mock_runner()
    report = scan(inventory(), run, tmp_path)
    assert report["bcd_integrity"] == "NOT_TESTED"
    assert report["windows_integrity"] == "NOT_TESTED"
    assert report["disks"][0]["volumes"][0]["result"] == "EVIDENCE_COLLECTED"

def test_mount_failure_cleans_up(tmp_path):
    run, calls = mock_runner(mount_failure=True)
    report = scan(inventory(), run, tmp_path)
    assert report["disks"][0]["volumes"][0]["result"] == "READ_ONLY_MOUNT_FAILED"
    assert not list(tmp_path.iterdir())

def test_bcd_header_only(tmp_path):
    (tmp_path / "BCD").write_bytes(b"regf" + b"0" * 32)
    assert file_evidence(tmp_path, "BCD", "hive")["result"] == "HEADER_RECOGNIZED"

def test_pending_sectors_classified_as_risk():
    smart = "SMART overall-health self-assessment test result: PASSED\n 197 Current_Pending_Sector 0x0032 100 100 050 Old_age Always - 4"
    assert parse_smart(smart)["physical_risk_indicated"]

def test_unapproved_device_path_skipped(tmp_path):
    fake = {"blockdevices": [{"name": "/tmp/unsafe", "type": "disk",
                              "tran": "ata", "rm": False}]}
    report = scan(fake, lambda args: (0, "", ""), tmp_path)
    assert report["disks"][0]["reason"] == "INVALID_DEVICE_NAME"
