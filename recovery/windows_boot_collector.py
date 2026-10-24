"""RedeTI v0.2: offline inspection on PRE-MOUNTED read-only NTFS volumes.

Reads at most 4096 bytes of each selected file. No repair, no mount, no write,
no BCD editing. Header recognition does not validate Windows/BCD integrity.
"""
from __future__ import annotations
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Callable, Optional

MountProbe = Callable[[Path], tuple[Optional[dict], Optional[str]]]
BOOT_FILES = (("bootmgr", "bootmgr", "nonempty"), ("bcd", "Boot/BCD", "registry"))
OS_FILES = (("winload", "Windows/System32/winload.exe", "pe"),
            ("kernel", "Windows/System32/ntoskrnl.exe", "pe"),
            ("system_hive", "Windows/System32/config/SYSTEM", "registry"))
ALLOWED_FS = {"ntfs3", "fuseblk", "ntfs"}

def query_mount(root: Path) -> tuple[Optional[dict], Optional[str]]:
    """Reject absent, non-NTFS and read-write mounts without mounting anything."""
    if not root.is_absolute() or root == Path("/") or root.is_symlink() or not root.is_dir():
        return None, "Mountpoint must be existing absolute non-symlink directory"
    try:
        p = subprocess.run(["findmnt", "--json", "--mountpoint", str(root),
                            "--output", "TARGET,SOURCE,FSTYPE,OPTIONS"],
                           capture_output=True, text=True, errors="replace",
                           timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"findmnt unavailable: {exc}"
    if p.returncode:
        return None, "No filesystem mounted exactly at this directory"
    try:
        entries = json.loads(p.stdout).get("filesystems", [])
        if len(entries) != 1:
            raise ValueError("ambiguous mounts")
        entry = entries[0]
        if entry.get("target") != str(root):
            raise ValueError("mount target mismatch")
        source, fstype, opts = (entry.get(k, "") for k in ("source", "fstype", "options"))
        if not isinstance(source, str) or not source.startswith("/dev/"):
            raise ValueError("not block-backed")
        if fstype not in ALLOWED_FS:
            raise ValueError("not recognized NTFS")
        if "ro" not in opts.split(","):
            raise ValueError("mount not read-only")
        return {"target": str(root), "source": source,
                "fstype": fstype, "read_only": True}, None
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        return None, f"Unsafe or unsupported mount: {exc}"

def examine_file(root: Path, relative: str, kind: str) -> dict:
    """Inspect fixed paths, refusing symlinks in each path component."""
    r = {"path": relative, "status": "NOT_TESTED",
         "size_bytes": None, "check": kind}
    try:
        parts = Path(relative).parts
        if any(x in ("..", ".") for x in parts):
            raise ValueError("Invalid relative path")
        current = root
        for part in parts:
            current = current / part
            st = os.lstat(current)
            if stat.S_ISLNK(st.st_mode):
                r["status"] = "REFUSED_SYMLINK"
                return r
        if not stat.S_ISREG(st.st_mode):
            r["status"] = "NOT_REGULAR_FILE"
            return r
        r["size_bytes"] = st.st_size
        fd = os.open(current, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_CLOEXEC", 0))
        try:
            head = os.read(fd, 4096)
        finally:
            os.close(fd)
        if not head or not st.st_size:
            r["status"] = "EMPTY"
        elif kind == "registry":
            r["status"] = ("HEADER_RECOGNIZED" if head[:4] == b"regf"
                           else "HEADER_UNRECOGNIZED")
        elif kind == "pe":
            if len(head) < 64 or head[:2] != b"MZ":
                r["status"] = "HEADER_UNRECOGNIZED"
            else:
                offset = int.from_bytes(head[0x3C:0x40], "little")
                r["status"] = ("HEADER_RECOGNIZED" if
                               offset + 4 <= len(head) and
                               head[offset:offset+4] == b"PE\x00\x00"
                               else "HEADER_UNRECOGNIZED")
        else:
            r["status"] = "PRESENT_UNVERIFIED"
        return r
    except FileNotFoundError:
        r["status"] = "MISSING"
    except (OSError, ValueError) as exc:
        r["status"] = "READ_ERROR"
        r["reason"] = type(exc).__name__
    return r

def inspect(boot_root: Path, windows_root: Path, probe: MountProbe = query_mount,
            expected_sources: Optional[set[str]] = None) -> dict:
    """Require two distinct read-only NTFS mounts; refuse unsupported targets."""
    roots = {"boot": Path(boot_root), "windows": Path(windows_root)}
    r = {"schema": "redeti.windows.boot.v0.2", "status": "BLOCKED",
         "read_only_collector": True, "repair_gate": "BLOCKED",
         "bcd_integrity": "NOT_TESTED", "windows_integrity": "NOT_TESTED",
         "boot_mode": "NOT_VERIFIED", "mounts": {}, "files": [], "findings": []}
    if roots["boot"] == roots["windows"]:
        r["findings"].append({"code": "SAME_MOUNTPOINT", "severity": "critical"})
        return r
    for role, root in roots.items():
        mount, err = probe(root)
        if err or not mount:
            r["findings"].append({"code": "READ_ONLY_MOUNT_REQUIRED", "role": role,
                                  "severity": "critical", "detail": err or "mount unavailable"})
            return r
        if (mount.get("target") != str(root) or mount.get("read_only") is not True
                or mount.get("fstype") not in ALLOWED_FS):
            r["findings"].append({"code": "MOUNT_VALIDATION_FAILED",
                                  "role": role, "severity": "critical"})
            return r
        if expected_sources is not None and mount.get("source") not in expected_sources:
            r["findings"].append({"code": "SOURCE_NOT_IN_INVENTORY",
                                  "role": role, "severity": "critical"})
            return r
        r["mounts"][role] = mount
    if r["mounts"]["boot"]["source"] == r["mounts"]["windows"]["source"]:
        r["findings"].append({"code": "SAME_SOURCE", "severity": "critical"})
        return r
    for role, files in (("boot", BOOT_FILES), ("windows", OS_FILES)):
        for name, relative, kind in files:
            item = examine_file(roots[role], relative, kind)
            item.update(id=name, volume=role)
            r["files"].append(item)
            if item["status"] in {"MISSING", "EMPTY", "HEADER_UNRECOGNIZED",
                                  "READ_ERROR", "REFUSED_SYMLINK", "NOT_REGULAR_FILE"}:
                r["findings"].append({"code": "FILE_CHECK_" + item["status"],
                                      "file": relative, "severity": "warning",
                                      "detail": "Manual verification required; no repair"})
    r["status"] = "COLLECTED_WITH_FINDINGS" if r["findings"] else "COLLECTED"
    return r
