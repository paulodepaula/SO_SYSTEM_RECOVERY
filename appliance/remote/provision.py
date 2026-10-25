"""Locate an explicitly labelled USB provisioning volume, never an internal disk.

Only lsblk metadata is queried. The mount is done separately, read-only.
"""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ALLOWED_LABELS = {"ventoy", "redeti_cfg"}
ALLOWED_FS = {"exfat", "vfat"}

def candidates(disks):
    found = []
    for disk in disks:
        if not isinstance(disk, dict) or disk.get("type") != "disk":
            continue
        if not (disk.get("tran") == "usb" or disk.get("rm") in (True, 1, "1")):
            continue
        for part in disk.get("children") or []:
            if not isinstance(part, dict) or part.get("type") != "part":
                continue
            name = part.get("name")
            if (isinstance(name, str) and name.startswith("/dev/")
                and (part.get("label") or "").casefold() in ALLOWED_LABELS
                and (part.get("fstype") or "").casefold() in ALLOWED_FS):
                found.append(name)
    # Do not guess when multiple USB partitions match.
    return found

def verified_ventoy_mappers(device, dev_root=Path("/dev"), sys_root=Path("/sys")):
    """Identify *existing* Ventoy mappings backed solely by this USB partition.

    Ventoy 1.1.01+ originally exposed /dev/mapper/sdXN while newer releases
    also use /dev/mapper/VentoyPart. Neither name is trusted on its own.
    """
    src_name = device.rsplit("/", 1)[-1]
    try:
        usb = (dev_root / src_name).resolve(strict=True)
    except OSError:
        return []
    found = []
    for alias in ("VentoyPart", src_name):
        mapper = dev_root / "mapper" / alias
        try:
            resolved = mapper.resolve(strict=True)
            if not re.fullmatch(r"dm-[0-9]+", resolved.name):
                continue
            if not stat.S_ISBLK(os.stat(resolved).st_mode):
                continue
            slaves = sys_root / "class" / "block" / resolved.name / "slaves"
            members = list(slaves.iterdir())
            if len(members) != 1:
                continue
            backing = (dev_root / members[0].name).resolve(strict=True)
            if backing != usb:
                continue
            if str(mapper) not in found:
                found.append(str(mapper))
        except (OSError, ValueError):
            continue
    return found


def verified_ventoy_mapper(device, dev_root=Path("/dev"), sys_root=Path("/sys")):
    """Backward-compatible single mapper API for older provisioning tests."""
    mappings = verified_ventoy_mappers(device, dev_root, sys_root)
    return mappings[0] if mappings else None


def sources(disks, dev_root=Path("/dev"), sys_root=Path("/sys")):
    """Return approved USB partition then only its verified Ventoy mappings."""
    volumes = candidates(disks)
    if len(volumes) != 1:
        return []
    src = volumes[0]
    matched = next(
        (p for d in disks if isinstance(d, dict)
         for p in d.get("children") or []
         if isinstance(p, dict) and p.get("name") == src), None
    )
    result = [src]
    if matched and (matched.get("label") or "").casefold() == "ventoy":
        result.extend(verified_ventoy_mappers(src, dev_root, sys_root))
    return result


def main():
    if sys.argv[1:] not in ([], ["sources"]):
        return 2
    cmd = ["lsblk", "--json", "--paths", "--output", "NAME,TYPE,LABEL,FSTYPE,RM,TRAN"]
    try:
        data = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
        devices = json.loads(data.stdout)["blockdevices"]
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return 2
    volumes = sources(devices) if sys.argv[1:] == ["sources"] else candidates(devices)
    if volumes:
        for device in volumes:
            print(device)
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
