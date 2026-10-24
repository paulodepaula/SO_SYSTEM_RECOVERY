"""Linux Rescue collection v0.2: observation only, no repair/mount operations.

All external tools run via fixed argument vectors (no shell). Live collection is
opt-in and never saves to a disk; reports are emitted to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Callable

Runner = Callable[[list[str]], tuple[int, str, str]]
DISK_PATH = re.compile(r"^/dev/(?:[a-zA-Z0-9_.-]+)$")
TRACKED_SMART = {5: "reallocated_sectors", 197: "pending_sectors", 198: "uncorrectable_sectors", 199: "udma_crc_errors"}


def safe_run(args: list[str]) -> tuple[int, str, str]:
    """Call only predefined commands; never a shell, repair, test or mount."""
    if args[0] not in {"lsblk", "smartctl", "fdisk"}:
        raise ValueError("Command not in observation allowlist")
    try:
        proc = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=25, check=False)
        return proc.returncode, proc.stdout[:100000], proc.stderr[:5000]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def smart_summary(output: str) -> dict:
    health = "unknown"
    match = re.search(r"SMART overall-health self-assessment test result:\s*(PASSED|FAILED)", output, re.I)
    if match:
        health = match.group(1).lower()
    attr: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 10 and parts[0].isdigit() and int(parts[0]) in TRACKED_SMART:
            # SMART raw value is firmware-specific; keep only plain integer counters.
            raw = parts[-1]
            if raw.isdecimal():
                attr[TRACKED_SMART[int(parts[0])]] = int(raw)
    return {"overall_health": health, "attributes": attr}


def collect(runner: Runner = safe_run) -> dict:
    args = ["lsblk", "--json", "--bytes", "--paths", "--output", "NAME,TYPE,SIZE,MODEL,SERIAL,TRAN,RO,RM,FSTYPE,PARTTYPE,PARTUUID,UUID,PTTYPE,MOUNTPOINTS"]
    code, output, err = runner(args)
    if code != 0:
        return {"schema": "redeti.linux.inventory.v0.2", "status": "error", "read_only_collector": True,
                "errors": [{"tool": "lsblk", "message": err or "lsblk failed"}], "disks": [], "findings": []}
    try:
        blockdevices = json.loads(output)["blockdevices"]
        if not isinstance(blockdevices, list):
            raise ValueError("not a device list")
    except (ValueError, KeyError, TypeError) as exc:
        return {"schema": "redeti.linux.inventory.v0.2", "status": "error", "read_only_collector": True,
                "errors": [{"tool": "lsblk", "message": "Invalid lsblk JSON: " + str(exc)}], "disks": [], "findings": []}

    report: dict = {"schema": "redeti.linux.inventory.v0.2", "status": "collected",
                    "read_only_collector": True, "repair_operations_available": False,
                    "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                    "disks": [], "findings": [], "warnings": []}
    for disk in blockdevices:
        if not isinstance(disk, dict) or disk.get("type") != "disk":
            continue
        path = disk.get("name", "")
        if not isinstance(path, str) or not DISK_PATH.fullmatch(path):
            report["warnings"].append("Ignored disk with invalid device path")
            continue
        device = {"path": path, "model": disk.get("model"), "serial": disk.get("serial"),
                  "size_bytes": disk.get("size"), "transport": disk.get("tran"),
                  "removable": bool(disk.get("rm")), "partition_table": disk.get("pttype"),
                  "partitions": disk.get("children", []), "smart": None, "fdisk_listing": None}
        report["disks"].append(device)
        if device["removable"] or device["transport"] == "usb":
            report["warnings"].append(f"{path}: removable/USB media not probed (Ventoy protection)")
            continue
        scode, smartout, smarterr = runner(["smartctl", "-H", "-A", "-i", path])
        device["smart"] = smart_summary(smartout)
        device["smart"]["tool_exit_code"] = scode
        if scode and not smartout:
            report["warnings"].append(f"{path}: SMART unavailable: {smarterr[:300]}")
        fcode, foutput, ferr = runner(["fdisk", "-l", path])
        if fcode == 0:
            # Observation only; contains boot flags and table type, not verified BCD.
            device["fdisk_listing"] = foutput[:15000]
        else:
            report["warnings"].append(f"{path}: fdisk read failed: {ferr[:300]}")
        sm = device["smart"]
        attr = sm["attributes"]
        if sm["overall_health"] == "failed" or any(attr.get(key, 0) > 0 for key in ("pending_sectors", "uncorrectable_sectors", "reallocated_sectors")):
            report["findings"].append({"code": "STORAGE_RISK", "disk": path, "severity": "critical",
                                       "recommendation": "Avoid writing to original media; evaluate preservation and professional recovery."})
        elif sm["overall_health"] == "unknown":
            report["findings"].append({"code": "SMART_NOT_VERIFIED", "disk": path, "severity": "warning",
                                       "recommendation": "SMART result inconclusive; no write operations authorized."})
        if attr.get("udma_crc_errors", 0) > 0:
            report["findings"].append({"code": "HISTORICAL_LINK_ERRORS", "disk": path, "severity": "info",
                                       "recommendation": "Inspect SATA connection if CRC errors increase; counter can be historical."})
    report["repair_gate"] = "BLOCKED"  # v0.2 always refuses writes
    report["bcd_integrity"] = "NOT_TESTED"
    report["windows_integrity"] = "NOT_TESTED"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RedeTI Recovery OS - Linux v0.2 read-only inventory")
    parser.add_argument("--live", action="store_true", help="explicitly permit observation of this local machine")
    parser.add_argument("--acknowledge-read-only", action="store_true", help="acknowledge no repairs or mounts will be run")
    args = parser.parse_args(argv)
    if not (args.live and args.acknowledge_read_only):
        parser.error("Live collection needs BOTH --live and --acknowledge-read-only")
    print(json.dumps(collect(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
