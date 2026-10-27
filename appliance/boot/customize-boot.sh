#!/usr/bin/env bash
# Runs ONLY inside sysrescue-customize unpacked ISO directory.
set -euo pipefail
# Modify bootloader configs without touching the host. Preserve rescue entries.
python3 - <<'PYSCRIPT'
from pathlib import Path
import re
root=Path.cwd()
changed=[]
# GRUB: keep visible for 3 seconds; allow E to edit and reach rescue options.
for p in (root/'boot/grub/grubsrcd.cfg',root/'boot/grub/grub.cfg'):
    if not p.is_file(): continue
    s=p.read_text(errors='replace')
    orig=s
    s=re.sub(r'(?m)^(\s*set\s+timeout=)[^\n]+',r'\g<1>3',s)
    s=re.sub(r'(?m)^(\s*set\s+timeout_style=)[^\n]+',r'\g<1>menu',s)
    # Only first normal boot entry; keep other entries verbose for diagnostics.
    lines=s.splitlines(keepends=True)
    for i,line in enumerate(lines):
        if re.match(r'^\s*linux(?:efi)?\s',line) and 'archisobasedir=' in line:
            if ' loglevel=' not in line:
                lines[i]=line.rstrip('\n')+' quiet loglevel=3 systemd.show_status=false rd.udev.log_level=3\n'
            break
    s=''.join(lines)
    if s!=orig: p.write_text(s);changed.append(str(p))
# BIOS Syslinux: timeout is measured in tenths of a second.
for p in (root/'sysresccd/boot/syslinux/sysresccd_head.cfg',root/'sysresccd/boot/syslinux/sysresccd.cfg',root/'isolinux/isolinux.cfg'):
    if not p.is_file():continue
    s=p.read_text(errors='replace'); orig=s
    if re.search(r'(?im)^\s*TIMEOUT\s+\d+',s):
        s=re.sub(r'(?im)^(\s*TIMEOUT\s+)\d+',r'\g<1>30',s)
    else: s='TIMEOUT 30\n'+s
    if s!=orig: p.write_text(s);changed.append(str(p))
# Syslinux boot flags in normal entry file only; keep alternate boot modes intact.
p=root/'sysresccd/boot/syslinux/sysresccd_sys.cfg'
if p.is_file():
    s=p.read_text(errors='replace');orig=s
    lines=s.splitlines(keepends=True)
    for i,line in enumerate(lines):
        if re.match(r'^\s*APPEND\s',line) and 'archisobasedir=' in line:
            if ' loglevel=' not in line:
                lines[i]=line.rstrip('\n')+' quiet loglevel=3 systemd.show_status=false rd.udev.log_level=3\n'
            break
    s=''.join(lines)
    if s!=orig: p.write_text(s);changed.append(str(p))
if not changed:
    raise SystemExit('ERRO: layouts de boot nao reconhecidos; abortando ISO')
print('Bootloader config customized:', ', '.join(changed))
PYSCRIPT
