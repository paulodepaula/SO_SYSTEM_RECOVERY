"""RedeTI Recovery OS - boot-time metadata-only hardware inventory.
No mounts, disk writes, SMART self-tests, shell, or HTTP.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable

LSBLK = ["lsblk", "--json", "--bytes", "--paths", "--output", "NAME,TYPE,SIZE,MODEL,TRAN,RM,FSTYPE,PTTYPE,PARTTYPE,PARTLABEL,MOUNTPOINTS"]
Runner = Callable[[list[str]], tuple[int, str, str]]
Read = Callable[[str], str]


def execute(argv: list[str]) -> tuple[int, str, str]:
    if argv != LSBLK:
        raise ValueError("Command outside read-only inventory allowlist")
    try:
        proc = subprocess.run(argv, text=True, errors="replace", capture_output=True, check=False, timeout=15)
        return proc.returncode, proc.stdout[:300000], proc.stderr[:1000]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def cpu_name(text: str) -> str:
    for line in text.splitlines():
        if ":" in line and line.split(":", 1)[0].strip().lower() in {"model name", "hardware", "processor"}:
            value = line.split(":", 1)[1].strip()
            if value and not value.isdecimal():
                return value[:150]
    return "Não identificado"


def memory_bytes(text: str) -> int | None:
    match = re.search(r"^MemTotal:\s*(\d+)\s*kB", text, re.M)
    return int(match.group(1)) * 1024 if match else None


def summarize_device(device: dict) -> dict:
    parts = []
    for part in device.get("children", []):
        if not isinstance(part, dict) or part.get("type") != "part":
            continue
        fs = str(part.get("fstype") or "")
        parts.append({
            "device": part.get("name"), "size_bytes": part.get("size"),
            "filesystem": fs or "Não identificado", "partition_type": part.get("parttype"),
            "partition_label": part.get("partlabel"),
        })
    usb = device.get("tran") == "usb" or bool(device.get("rm"))
    windows_possible = any(p["filesystem"].lower() == "ntfs" for p in parts)
    encrypted = any("bitlocker" in p["filesystem"].lower() for p in parts)
    return {
        "device": device.get("name"), "model": str(device.get("model") or "Desconhecido").strip(),
        "size_bytes": device.get("size"), "transport": device.get("tran"),
        "partition_table": device.get("pttype"), "is_removable_or_usb": usb,
        "partitions": parts,
        "windows_candidate": bool(windows_possible and not usb),
        "encrypted_partitions_possible": encrypted,
    }


def collect(runner: Runner = execute, reader: Read = read_text,
            efi_present: bool | None = None, logical_cpus: int | None = None) -> dict:
    """Initial recognition. NTFS means possible Windows, never confirmed."""
    if efi_present is None:
        efi_present = Path("/sys/firmware/efi").is_dir()
    base: dict = {
        "schema": "redeti.appliance.hardware.v0.5", "read_only": True,
        "writes_to_disks": False, "mounts_performed": False,
        "operating_system_confirmation": "NOT_TESTED",
        "cpu": {"model": cpu_name(reader("/proc/cpuinfo")),
                "logical_processors": logical_cpus if logical_cpus is not None else (os.cpu_count() or 0)},
        "ram_bytes": memory_bytes(reader("/proc/meminfo")),
        "recovery_boot_firmware": "UEFI" if efi_present else "BIOS/Legacy",
        "windows_boot_firmware": "NOT_VERIFIED",
        "disks": [], "target": {"status": "UNKNOWN", "message": "Inventário não concluído"},
        "warnings": [],
    }
    code, out, err = runner(LSBLK)
    if code != 0:
        base["warnings"].append("Inventário lsblk indisponível: " + err[:160])
        return base
    try:
        devices = json.loads(out)["blockdevices"]
        if not isinstance(devices, list):
            raise ValueError("Invalid inventory")
    except (ValueError, KeyError, TypeError):
        base["warnings"].append("Formato do inventário inválido")
        return base
    base["disks"] = [summarize_device(d) for d in devices if isinstance(d, dict) and d.get("type") == "disk"]
    internals = [d for d in base["disks"] if not d["is_removable_or_usb"]]
    candidates = [d for d in internals if d["windows_candidate"]]
    if len(internals) == 0:
        base["target"] = {"status": "NO_INTERNAL_DISK", "message": "Nenhum disco interno identificado"}
    elif len(internals) > 1:
        base["target"] = {"status": "MULTIPLE_INTERNAL_DISKS", "message": "Escolha supervisionada necessária"}
    elif len(candidates) == 1:
        base["target"] = {"status": "WINDOWS_CANDIDATE", "device": candidates[0]["device"],
                          "message": "Partição NTFS identificada; Windows não confirmado"}
    else:
        base["target"] = {"status": "INTERNAL_DISK_ONLY", "device": internals[0]["device"],
                          "message": "Disco identificado, sistema operacional não confirmado"}
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="RedeTI Recovery OS: inventário inicial automático e somente leitura")
    parser.add_argument("--output", default="-", help="- = stdout; outro caminho apenas sob /run/redeti")
    args = parser.parse_args()
    result = json.dumps(collect(), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(result)
    else:
        path = Path(args.output)
        if not path.is_absolute() or not path.is_relative_to(Path("/run/redeti")):
            parser.error("Saída somente sob /run/redeti (temporário em RAM)")
        if not Path("/run").is_mount():
            parser.error("/run não confirmado como ponto de montagem temporário")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
