import json
from pathlib import Path
from recovery.engine import analyze

BASE = Path(__file__).resolve().parents[1] / "fixtures"

def read(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))

def test_bcd_report_is_simulation_only():
    r = analyze(read("bcd-corrupt.json"))
    assert "BCD_INVALID" in [f["id"] for f in r["findings"]]
    assert r["repair_gate"] == "MANUAL_REVIEW_REQUIRED"
    assert not r["write_operations_enabled"]
    assert all(a["status"] == "SIMULATION_ONLY_NOT_EXECUTABLE" for a in r["proposed_actions"])

def test_failing_disk_blocks_repairs():
    r = analyze(read("failing-disk.json"))
    assert r["repair_gate"] == "BLOCKED"
    assert "PHYSICAL_RISK" in [f["id"] for f in r["findings"]]

def test_locked_bitlocker_blocks_repairs():
    r = analyze(read("bitlocker-locked.json"))
    assert r["repair_gate"] == "BLOCKED"

def test_no_disks_and_no_windows():
    r = analyze({"kind":"redeti_lab_fixture","disks":[],"windows_installations":[]})
    assert r["repair_gate"] == "MANUAL_REVIEW_REQUIRED"
    assert "DISK_MISSING" in [f["id"] for f in r["findings"]]
