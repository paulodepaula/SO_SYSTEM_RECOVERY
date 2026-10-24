"""Combined v0.2 inventory + boot evidence. Stdout JSON; no writes or mounts."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

if __package__:
    from .linux_collector import collect
    from .windows_boot_collector import inspect, query_mount
else:
    from linux_collector import collect
    from windows_boot_collector import inspect, query_mount

def _disk_for_partition(inventory: dict, source: str):
    for disk in inventory.get("disks", []):
        for part in disk.get("partitions", []):
            if part.get("name") == source:
                return disk
    return None

def diagnose(boot_root: Path, windows_root: Path, inventory_func=collect,
             windows_func=inspect) -> dict:
    storage = inventory_func()
    r = {"schema": "redeti.combined.diagnostic.v0.2", "status": "BLOCKED",
         "read_only": True, "repair_gate": "BLOCKED", "storage": storage,
         "windows_boot": {"status": "NOT_RUN", "reason": "Storage preflight incomplete"}}
    if storage.get("status") != "collected" or not storage.get("disks"):
        return r
    if any(f.get("code") == "STORAGE_RISK" for f in storage.get("findings", [])):
        r["windows_boot"]["reason"] = "Storage risk; preserve media before further reads"
        return r
    # For production collector, confirm each mounted volume is in the same
    # internal non-removable disk captured in the storage inventory.
    if windows_func is inspect:
        a, ae = query_mount(Path(boot_root))
        b, be = query_mount(Path(windows_root))
        if ae or be or not a or not b:
            r["windows_boot"] = {"status": "NOT_RUN",
                                 "reason": "Read-only NTFS volumes are not available",
                                 "details": [ae, be]}
            return r
        disk_a = _disk_for_partition(storage, a["source"])
        disk_b = _disk_for_partition(storage, b["source"])
        if (not disk_a or disk_a is not disk_b or disk_a.get("removable")
                or disk_a.get("transport") == "usb"):
            r["windows_boot"] = {"status": "NOT_RUN",
                                 "reason": "Volumes do not belong to the same non-USB disk"}
            return r
        r["windows_boot"] = windows_func(Path(boot_root), Path(windows_root),
                                          expected_sources={a["source"], b["source"]})
    else:
        # Dependency injection exclusively for offline unit tests.
        r["windows_boot"] = windows_func(Path(boot_root), Path(windows_root))
    r["status"] = ("COLLECTED" if r["windows_boot"].get("status", "").startswith("COLLECTED")
                   else "PARTIAL")
    return r

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="RedeTI v0.2: read-only Linux + Windows boot evidence")
    p.add_argument("--live", action="store_true")
    p.add_argument("--acknowledge-read-only", action="store_true")
    p.add_argument("--boot-root", default="/mnt/redeti-boot")
    p.add_argument("--windows-root", default="/mnt/redeti-windows")
    args = p.parse_args(argv)
    if not (args.live and args.acknowledge_read_only):
        p.error("Both --live and --acknowledge-read-only are required")
    print(json.dumps(diagnose(Path(args.boot_root), Path(args.windows_root)),
                     ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
