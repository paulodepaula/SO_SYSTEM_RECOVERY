"""RedeTI Recovery OS v0.3: automated read-only Windows assessment on Linux Rescue.
No repairs; temporary read-only mounts on RAM, automatic cleanup.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

EFI_GUID = 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b'
DEV_RE = re.compile('^/dev/[a-zA-Z0-9_.-]+$')
FILES_NTFS = {'bootmgr': ('bootmgr', 'nonempty'), 'bcd': ('Boot/BCD', 'hive'), 'winload': ('Windows/System32/winload.exe', 'pe'), 'kernel': ('Windows/System32/ntoskrnl.exe', 'pe'), 'system_hive': ('Windows/System32/config/SYSTEM', 'hive')}
FILES_EFI = {'efi_bootloader': ('EFI/Microsoft/Boot/bootmgfw.efi', 'pe'), 'efi_bcd': ('EFI/Microsoft/Boot/BCD', 'hive')}

def command(argv: list[str], timeout: int=20) -> tuple[int, str, str]:
    """Fixed commands, never a shell; no tests/recovery/writing options."""
    if argv[0] not in {'lsblk', 'smartctl', 'findmnt', 'mount', 'umount'}:
        raise ValueError('Prohibited command')
    try:
        p = subprocess.run(argv, capture_output=True, text=True, errors='replace', timeout=timeout, check=False)
        return (p.returncode, p.stdout[:120000], p.stderr[:2000])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (127, '', str(exc))

def file_evidence(root: Path, rel: str, kind: str) -> dict:
    """Read up to 4096 bytes, refusing symlinks and nonregular files."""
    info = {'file': rel, 'result': 'UNREADABLE'}
    current = root
    try:
        for part in Path(rel).parts:
            if part in ('.', '..'):
                raise ValueError('Invalid path')
            current = current / part
            st = os.lstat(current)
            if stat.S_ISLNK(st.st_mode):
                return {**info, 'result': 'SYMLINK_REFUSED'}
        if not stat.S_ISREG(st.st_mode):
            return {**info, 'result': 'NOT_REGULAR'}
        fd = os.open(current, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        try:
            head = os.read(fd, 4096)
        finally:
            os.close(fd)
        info['size_bytes'] = st.st_size
        if not head:
            info['result'] = 'EMPTY'
        elif kind == 'hive':
            info['result'] = 'HEADER_RECOGNIZED' if head.startswith(b'regf') else 'HEADER_UNRECOGNIZED'
        elif kind == 'pe':
            offset = int.from_bytes(head[60:64], 'little') if len(head) >= 64 else 0
            info['result'] = 'HEADER_RECOGNIZED' if head[:2] == b'MZ' and offset >= 64 and (offset + 4 <= len(head)) and (head[offset:offset + 4] == b'PE\x00\x00') else 'HEADER_UNRECOGNIZED'
        else:
            info['result'] = 'PRESENT_UNVERIFIED'
    except FileNotFoundError:
        info['result'] = 'MISSING'
    except (OSError, ValueError) as exc:
        info['error'] = type(exc).__name__
    return info

def parse_smart(data: str) -> dict:
    m = re.search('SMART overall-health self-assessment test result:\s*(PASSED|FAILED)', data, re.I)
    health = m.group(1).lower() if m else 'unknown'
    values = {}
    for line in data.splitlines():
        fields = line.split()
        if len(fields) > 9 and fields[0] in {'5', '197', '198', '199'} and fields[-1].isdigit():
            values[fields[0]] = int(fields[-1])
    risk = health == 'failed' or any((values.get(n, 0) > 0 for n in ('5', '197', '198')))
    return {'health': health, 'counters': values, 'physical_risk_indicated': risk}

def _partitions(disk: dict) -> list[dict]:
    return [x for x in disk.get('children', []) if isinstance(x, dict) and x.get('type') == 'part']

def _fs_mode(part: dict) -> str | None:
    fs = str(part.get('fstype') or '').lower()
    if fs == 'ntfs':
        return 'ntfs'
    if fs in {'vfat', 'fat32'} and str(part.get('parttype') or '').lower() == EFI_GUID:
        return 'efi'
    return None

def _mounted(part: dict, runner) -> bool:
    return bool(part.get('mountpoints') and any((x for x in part['mountpoints'])))

def _verified_mount(source: str, path: Path, runner) -> bool:
    code, out, _ = runner(['findmnt', '--json', '--mountpoint', str(path), '--output', 'SOURCE,TARGET,FSTYPE,OPTIONS'])
    if code:
        return False
    try:
        fs = json.loads(out)['filesystems']
        entry = fs[0]
        return len(fs) == 1 and entry.get('target') == str(path) and (entry.get('source') == source) and ('ro' in entry.get('options', '').split(',')) and (entry.get('fstype') in {'fuseblk', 'ntfs3', 'vfat'})
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        return False

def scan(inventory: dict, runner=command, mount_root: Path | None=None) -> dict:
    """Auto-detect eligible non-removable disks; mount NTFS/ESP only read-only."""
    report = {'schema': 'redeti.auto.v0.3', 'collected_at_utc': datetime.now(timezone.utc).isoformat(), 'mode': 'READ_ONLY_AUTOMATIC', 'repairs': 'DISABLED', 'bcd_integrity': 'NOT_TESTED', 'windows_integrity': 'NOT_TESTED', 'disks': [], 'findings': [], 'warnings': []}
    for disk in inventory.get('blockdevices', []):
        if disk.get('type') != 'disk':
            continue
        name = str(disk.get('name') or '')
        item = {'device': name, 'model': disk.get('model'), 'size_bytes': disk.get('size'), 'partition_table': disk.get('pttype'), 'status': 'SKIPPED', 'smart': None, 'volumes': []}
        report['disks'].append(item)
        if not DEV_RE.fullmatch(name):
            item['reason'] = 'INVALID_DEVICE_NAME'
            continue
        if disk.get('rm') or disk.get('tran') == 'usb':
            item['reason'] = 'USB_OR_REMOVABLE_PROTECTED'
            continue
        if disk.get('tran') not in {'ata', 'sata', 'nvme', 'sas', 'scsi', 'virtio'}:
            item['reason'] = 'UNKNOWN_TRANSPORT_REQUIRES_REVIEW'
            continue
        code, out, err = runner(['smartctl', '-H', '-A', '-i', name])
        sm = parse_smart(out)
        item['smart'] = sm
        if sm['physical_risk_indicated']:
            item['reason'] = 'STORAGE_RISK_NO_FURTHER_SCAN'
            report['findings'].append({'disk': name, 'code': 'STORAGE_RISK', 'level': 'critical'})
            continue
        if sm['health'] != 'passed' or code != 0:
            item['reason'] = 'SMART_INCONCLUSIVE_NO_MOUNT'
            continue
        item['status'] = 'SCANNED'
        for part in _partitions(disk)[:16]:
            path = str(part.get('name') or '')
            fs_mode = _fs_mode(part)
            if not DEV_RE.fullmatch(path) or fs_mode is None:
                continue
            volume = {'source': path, 'filesystem': fs_mode, 'result': 'SKIPPED', 'files': []}
            item['volumes'].append(volume)
            if _mounted(part, runner):
                volume['result'] = 'ALREADY_MOUNTED_SKIPPED'
                continue
            if mount_root is None:
                volume['result'] = 'NO_RAM_DIRECTORY'
                continue
            # os.rmdir only; never recursively delete a possibly mounted volume.
            mountpoint = Path(tempfile.mkdtemp(prefix='volume-', dir=mount_root))
            mounted_by_us = False
            try:
                if fs_mode == 'ntfs':
                    args = ['mount', '-t', 'ntfs-3g', '-o', 'ro,norecover,nodev,nosuid,noexec', path, str(mountpoint)]
                else:
                    args = ['mount', '-t', 'vfat', '-o', 'ro,nodev,nosuid,noexec', path, str(mountpoint)]
                code, _, err = runner(args)
                if code:
                    volume['result'] = 'READ_ONLY_MOUNT_FAILED'
                    volume['error'] = err[:180]
                else:
                    mounted_by_us = True
                    if not _verified_mount(path, mountpoint, runner):
                        volume['result'] = 'MOUNT_VERIFICATION_FAILED'
                    else:
                        files = FILES_NTFS if fs_mode == 'ntfs' else FILES_EFI
                        volume['files'] = [{'id': key, **file_evidence(mountpoint, rel, kind)} for key, (rel, kind) in files.items()]
                        volume['result'] = 'EVIDENCE_COLLECTED'
            finally:
                if mounted_by_us:
                    ucode, _, uerr = runner(['umount', str(mountpoint)])
                    if ucode:
                        volume['result'] = 'UNMOUNT_FAILED'
                        volume['error'] = uerr[:180]
                        report['warnings'].append(f'Unmount failed for {path}; inspect live mount state')
                    else:
                        os.rmdir(mountpoint)
                else:
                    check, _, _ = runner(['findmnt', '--mountpoint', str(mountpoint)])
                    if check:
                        os.rmdir(mountpoint)
                    else:
                        volume['result'] = 'MOUNT_UNEXPECTEDLY_ACTIVE'
                        report['warnings'].append(f'Mount active after failed command: {path}')
    return report

def run_live() -> dict:
    code, fs, _ = command(['findmnt', '-no', 'FSTYPE', '--target', '/run'])
    if code or fs.strip() != 'tmpfs':
        return {'schema': 'redeti.auto.v0.3', 'error': 'NO_RAM_BACKED_RUN', 'repairs': 'DISABLED'}
    code, out, err = command(['lsblk', '--json', '--bytes', '--paths', '--output', 'NAME,TYPE,SIZE,MODEL,TRAN,RM,FSTYPE,PARTTYPE,PTTYPE,MOUNTPOINTS'])
    if code:
        return {'schema': 'redeti.auto.v0.3', 'error': 'LSBLK_FAILED', 'details': err[:180], 'repairs': 'DISABLED'}
    try:
        inventory = json.loads(out)
        if not isinstance(inventory.get('blockdevices'), list):
            raise ValueError('missing devices')
    except (ValueError, TypeError, AttributeError):
        return {'schema': 'redeti.auto.v0.3', 'error': 'INVENTORY_INVALID', 'repairs': 'DISABLED'}
    td = Path(tempfile.mkdtemp(prefix='redeti-auto-', dir='/run'))
    try:
        return scan(inventory, mount_root=td)
    finally:
        try:
            os.rmdir(td)
        except OSError:
            pass

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='RedeTI Recovery OS v0.3 - automated read-only scan')
    p.add_argument('--live', action='store_true', help='read local disk metadata and selected files')
    p.add_argument('--acknowledge-read-only', action='store_true', help='confirm temporary ro mounts permitted')
    args = p.parse_args(argv)
    if not (args.live and args.acknowledge_read_only):
        p.error('Use --live --acknowledge-read-only to allow read-only scan')
    print(json.dumps(run_live(), ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
