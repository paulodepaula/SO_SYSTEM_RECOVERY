from recovery.auto_scan import scan

def test_multiple_internal_drives_skip_all(tmp_path):
    data = {"blockdevices": [
        {"name": "/dev/sda", "type": "disk", "tran": "ata", "rm": False},
        {"name": "/dev/nvme0n1", "type": "disk", "tran": "nvme", "rm": False},
    ]}
    calls = []
    def runner(args):
        calls.append(args)
        return 0, "", ""
    report = scan(data, runner, tmp_path)
    assert any("MULTIPLE_INTERNAL_DISKS" in warning for warning in report["warnings"])
    assert not calls
