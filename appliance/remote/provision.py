"""Locate an explicitly labelled USB provisioning volume, never an internal disk.

Only lsblk metadata is queried. The mount is done separately, read-only.
"""
import json
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

def main():
    cmd = ["lsblk", "--json", "--paths", "--output", "NAME,TYPE,LABEL,FSTYPE,RM,TRAN"]
    try:
        data = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
        devices = json.loads(data.stdout)["blockdevices"]
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return 2
    volumes = candidates(devices)
    if len(volumes) == 1:
        print(volumes[0])
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
