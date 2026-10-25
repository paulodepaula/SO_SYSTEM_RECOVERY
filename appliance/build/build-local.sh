#!/usr/bin/env bash
# Hermes appliance ISO builder. Builds only after precompiled native ELF exists.
set -euo pipefail
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo "Uso: build-local.sh SYSTEMRESCUE_13.02.ISO [OUTDIR]" >&2; exit 2; }
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
base="$(realpath -e -- "$1")"
outdir="${2:-$HOME/RecoveryOS/out}"
mkdir -p -- "$outdir"
outdir="$(realpath -e -- "$outdir")"
[ "$(basename -- "$base")" = "systemrescue-13.02-amd64.iso" ] || exit 2
expected="ad4d670b72859d887c7960142a9a9d36a3e50446694a035e254442f65d6e7572"
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected" ] || { echo "Invalid ISO base checksum" >&2; exit 3; }
ui="${REDETI_APPLIANCE_WORK:-$HOME/RecoveryOS/native-build}/out/redeti-ui"
[ -s "$ui" ] && [ -f "$ui.sha256" ] || { echo "Native ELF not yet built" >&2; exit 4; }
(cd -- "$(dirname -- "$ui")" && sha256sum -c "$(basename -- "$ui").sha256")
[ "$(df -Pk "$outdir" | awk 'NR==2 {print $4}')" -ge 8388608 ] || { echo "8 GiB free space required" >&2; exit 5; }
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
iso="$outdir/RedeTI-Recovery-OS-appliance-$stamp.iso"
bash "$root/appliance/build/compose-appliance.sh" "$base" "$ui" "$iso"
xorriso -indev "$iso" -ls /sysresccd >/dev/null 2>&1
xorriso -indev "$iso" -ls /sysrescue.d >/dev/null 2>&1
(cd -- "$outdir"; sha256sum "$(basename -- "$iso")" > "$(basename -- "$iso").sha256")
echo "ISO created: $iso"
echo "NOT validated as bootable appliance until VM DRM/KMS smoke test passes."
echo "Older ISOs preserved for now: call retention script only after QEMU approval."
