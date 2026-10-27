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
# Accept both the old Docker '/out/redeti-ui' and new portable sidecars.
# Verify the digest against the exact ELF path on Hermes, never the name in sidecar.
stored="$(awk 'NR==1 {print $1}' "$ui.sha256")"
if [[ ! "$stored" =~ ^[0-9a-fA-F]{64}$ ]]; then
  echo "Invalid ELF checksum sidecar" >&2
  exit 4
fi
computed="$(sha256sum -- "$ui" | cut -d ' ' -f1)"
if [ "${stored,,}" != "$computed" ]; then
  echo "Native ELF checksum mismatch" >&2
  exit 4
fi
echo "Native ELF SHA256: OK"
# A valid digest alone does not prove this binary was built from current main.
command -v git >/dev/null || { echo "Git is required for build provenance" >&2; exit 4; }
[ -f "$ui.commit" ] || { echo "Native ELF missing source commit; rebuild first" >&2; exit 4; }
source_commit="$(tr -d '[:space:]' < "$ui.commit")"
current_commit="$(git -C "$root" rev-parse --verify HEAD)"
[ "$source_commit" = "$current_commit" ] || {
  echo "Stale native ELF: built from $source_commit; current source $current_commit" >&2
  exit 4
}
git -C "$root" diff --quiet && git -C "$root" diff --cached --quiet || {
  echo "Tracked source modifications present; refusing ISO composition" >&2
  exit 4
}
echo "Native ELF commit: $source_commit"
# Preserve exactly the build/version shown on-screen in the ISO manifest.
[ -s "$ui.buildinfo" ] || { echo "Native ELF missing build identity; recompile first" >&2; exit 4; }
grep -Fx "source_commit=$current_commit" "$ui.buildinfo" >/dev/null || {
  echo "Native build identity does not match current commit" >&2
  exit 4
}
build_tag="$(sed -n 's/^build_tag=//p' "$ui.buildinfo")"
app_version="$(sed -n 's/^app_version=//p' "$ui.buildinfo")"
[[ "$build_tag" =~ ^b[0-9]{6}-[0-9]{6}$ ]] || { echo "Invalid native build identity" >&2; exit 4; }
[[ "$app_version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Invalid application version" >&2; exit 4; }
echo "Native build: $app_version | $build_tag | ${source_commit:0:8}"

# Download once and then reuse small static VPN binaries. No secrets embedded.
bash "$root/appliance/build/fetch-tailscale.sh"
[ "$(df -Pk "$outdir" | awk 'NR==2 {print $4}')" -ge 8388608 ] || { echo "8 GiB free space required" >&2; exit 5; }
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
# Include the source revision in the filename to avoid Windows/QEMU ISO mixups.
revision="${current_commit:0:8}"
iso="$outdir/RedeTI-Recovery-OS-appliance-$revision-$stamp.iso"
bash "$root/appliance/build/compose-appliance.sh" "$base" "$ui" "$iso"
xorriso -indev "$iso" -ls /sysresccd >/dev/null 2>&1
xorriso -indev "$iso" -ls /sysrescue.d >/dev/null 2>&1
(cd -- "$outdir"; sha256sum "$(basename -- "$iso")" > "$(basename -- "$iso").sha256")
# Portable build manifest: compare the ISO checksum with Windows Get-FileHash.
{
  printf 'app_version=%s\n' "$app_version"
  printf 'build_tag=%s\n' "$build_tag"
  printf 'source_commit=%s\n' "$current_commit"
  printf 'elf_sha256=%s\n' "$computed"
  printf 'iso_sha256=%s\n' "$(sha256sum "$iso" | cut -d ' ' -f 1)"
  printf 'iso_filename=%s\n' "$(basename -- "$iso")"
} > "$iso.buildinfo"
report_args=(
  --repo-root "$root"
  --stage "${REDETI_REPORT_STAGE:-BOOT-2}"
  --commit "$current_commit"
  --iso "$iso"
  --compile-result PASS
  --test "Native ELF checksum and source commit verified"
  --test "ISO structure and BIOS/UEFI records checked with xorriso"
  --pending "Homologação física BIOS/Legacy e UEFI"
  --pending "Validação visual DRM/KMS em hardware real"
)
if [ -n "${REDETI_REPORT_SINCE:-}" ]; then
  report_args+=(--since "$REDETI_REPORT_SINCE")
fi
python3 "$root/scripts/generate-recovery-report.py" "${report_args[@]}"
echo "ISO created: $iso"
echo "Source revision: $current_commit"
echo "ISO SHA256: $(sha256sum "$iso" | cut -d ' ' -f 1)"
echo "Check the Windows/QEMU copy against the .sha256 before calling it current."
echo "NOT validated as bootable appliance until VM DRM/KMS smoke test passes."
echo "Older ISOs preserved for now: call retention script only after QEMU approval."
