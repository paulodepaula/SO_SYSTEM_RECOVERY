from recovery.windows_boot_collector import inspect, query_mount
from recovery.diagnose import diagnose

def make_files(tmp_path):
    boot, win = tmp_path / "boot", tmp_path / "windows"
    (boot / "Boot").mkdir(parents=True)
    (win / "Windows" / "System32" / "config").mkdir(parents=True)
    (boot / "bootmgr").write_bytes(b"BOOTMGR")
    (boot / "Boot" / "BCD").write_bytes(b"regf" + b"0" * 32)
    pe = bytearray(256)
    pe[:2] = b"MZ"
    pe[0x3C:0x40] = (128).to_bytes(4, "little")
    pe[128:132] = b"PE\x00\x00"
    (win / "Windows" / "System32" / "winload.exe").write_bytes(pe)
    (win / "Windows" / "System32" / "ntoskrnl.exe").write_bytes(pe)
    (win / "Windows" / "System32" / "config" / "SYSTEM").write_bytes(b"regf" + b"0" * 32)
    return boot, win

def probe_for(boot, win, ro=True):
    def probe(path):
        return {"target": str(path), "source": "/dev/sda1" if path == boot else "/dev/sda2",
                "read_only": ro, "fstype": "ntfs3"}, None
    return probe

def test_headers_are_not_claimed_as_integrity(tmp_path):
    boot, win = make_files(tmp_path)
    r = inspect(boot, win, probe=probe_for(boot, win))
    assert r["status"] == "COLLECTED"
    assert r["repair_gate"] == "BLOCKED"
    assert r["bcd_integrity"] == "NOT_TESTED"
    assert r["windows_integrity"] == "NOT_TESTED"
    assert len(r["files"]) == 5
    assert all(x["status"] in {"HEADER_RECOGNIZED", "PRESENT_UNVERIFIED"} for x in r["files"])

def test_read_write_mount_blocked(tmp_path):
    boot, win = make_files(tmp_path)
    r = inspect(boot, win, probe=probe_for(boot, win, ro=False))
    assert r["status"] == "BLOCKED"
    assert not r["files"]

def test_missing_bcd_flagged(tmp_path):
    boot, win = make_files(tmp_path)
    (boot / "Boot" / "BCD").unlink()
    r = inspect(boot, win, probe=probe_for(boot, win))
    assert next(x for x in r["files"] if x["id"] == "bcd")["status"] == "MISSING"
    assert r["repair_gate"] == "BLOCKED"

def test_bad_header_distinguished_from_bcd_integrity(tmp_path):
    boot, win = make_files(tmp_path)
    (boot / "Boot" / "BCD").write_bytes(b"abcd")
    r = inspect(boot, win, probe=probe_for(boot, win))
    assert next(x for x in r["files"] if x["id"] == "bcd")["status"] == "HEADER_UNRECOGNIZED"
    assert r["bcd_integrity"] == "NOT_TESTED"

def test_symlink_refused(tmp_path):
    boot, win = make_files(tmp_path)
    (boot / "Boot" / "BCD").unlink()
    (boot / "Boot" / "BCD").symlink_to(win / "Windows" / "System32" / "config" / "SYSTEM")
    r = inspect(boot, win, probe=probe_for(boot, win))
    assert next(x for x in r["files"] if x["id"] == "bcd")["status"] == "REFUSED_SYMLINK"

def test_mount_not_present_blocked(tmp_path):
    m = tmp_path / "not-mounted"
    m.mkdir()
    mount, err = query_mount(m)
    assert mount is None and err

def test_wrong_inventory_source_blocked(tmp_path):
    boot, win = make_files(tmp_path)
    r = inspect(boot, win, probe=probe_for(boot, win), expected_sources={"/dev/sdc1", "/dev/sdc2"})
    assert r["status"] == "BLOCKED"
    assert not r["files"]

def test_same_root_blocked(tmp_path):
    boot, _ = make_files(tmp_path)
    assert inspect(boot, boot, probe=probe_for(boot, boot))["status"] == "BLOCKED"

def test_storage_risk_blocks_boot_scan(tmp_path):
    boot, win = make_files(tmp_path)
    inv = lambda: {"status": "collected", "disks": [{"path": "/dev/sda"}],
                   "findings": [{"code": "STORAGE_RISK"}]}
    r = diagnose(boot, win, inventory_func=inv)
    assert r["status"] == "BLOCKED"
    assert r["windows_boot"]["status"] == "NOT_RUN"
