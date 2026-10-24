import json
from recovery.linux_collector import collect, smart_summary


def fake_runner(cmd):
    if cmd[0] == "lsblk":
        return 0, json.dumps({"blockdevices": [
            {"name": "/dev/sda", "type": "disk", "size": 512110190592, "tran": "sata", "rm": False, "pttype": "dos", "children": [{"name": "/dev/sda1", "type": "part", "fstype": "ntfs"}]},
            {"name": "/dev/sdb", "type": "disk", "size": 64000000000, "tran": "usb", "rm": True, "pttype": "dos"}
        ]}), ""
    if cmd[0] == "smartctl":
        return 0, "SMART overall-health self-assessment test result: PASSED\n  5 Reallocated_Sector_Ct 0x 100 100 050 Old_age Always - 0\n197 Current_Pending_Sector 0x 100 100 050 Old_age Always - 0\n199 UDMA_CRC_Error_Count 0x 100 100 050 Old_age Always - 1", ""
    if cmd[0] == "fdisk":
        return 0, "Disklabel type: dos\n/dev/sda1 * 2048 104447 102400 50M 7 HPFS/NTFS/exFAT", ""
    raise AssertionError("Unexpected command " + repr(cmd))


def test_reports_disks_and_preserves_usb():
    calls = []
    def runner(args):
        calls.append(args)
        return fake_runner(args)
    report = collect(runner)
    assert report["repair_gate"] == "BLOCKED"
    assert report["disks"][0]["partition_table"] == "dos"
    assert report["disks"][1]["smart"] is None
    assert any("Ventoy" in s for s in report["warnings"])
    assert not any(a[0] in {"mount", "ntfsfix", "fsck", "dd", "bcdboot"} for a in calls)
    assert len(calls) == 3  # lsblk, smartctl and fdisk on SATA, none on USB


def test_crc_historical_does_not_mark_disk_physically_failed():
    report = collect(fake_runner)
    assert "HISTORICAL_LINK_ERRORS" in {f["code"] for f in report["findings"]}
    assert "STORAGE_RISK" not in {f["code"] for f in report["findings"]}


def test_missing_lsblk_fails_closed():
    report = collect(lambda args: (127, "", "lsblk not found"))
    assert report["status"] == "error"
    assert report["disks"] == []


def test_bad_json_fails_closed():
    report = collect(lambda args: (0, "wrong", ""))
    assert report["status"] == "error"


def test_smart_with_pending_sectors_is_risk():
    def bad_smart(args):
        code, out, err = fake_runner(args)
        if args[0] == "smartctl":
            out = out.replace(" 050 Old_age Always - 0\n199", " 050 Old_age Always - 2\n199")
        return code, out, err
    assert "STORAGE_RISK" in {x["code"] for x in collect(bad_smart)["findings"]}


def test_smart_unknown_does_not_claim_healthy():
    assert smart_summary("Device is not supported")["overall_health"] == "unknown"
