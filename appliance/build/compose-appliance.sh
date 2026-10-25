#!/usr/bin/env bash
# Build a distinct direct-boot appliance ISO (never touches the old web recipe).
# Usage: bash appliance/build/compose-appliance.sh SYSTEMRESCUE_BASE.ISO REDETI_UI OUTPUT.ISO
set -euo pipefail
[ "$#" -eq 3 ] || { echo "Uso: compose-appliance.sh SYSTEMRESCUE_BASE.ISO REDETI_UI OUTPUT.ISO" >&2; exit 2; }
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source_iso="$(realpath -e -- "$1")"
binary="$(realpath -e -- "$2")"
output="$(realpath -m -- "$3")"
[ -f "$source_iso" ] && [ -f "$binary" ] && [ ! -L "$binary" ] || exit 2
[ ! -e "$output" ] || { echo "Dest exists; no overwrite" >&2; exit 2; }
[ "$source_iso" != "$output" ] || exit 2
for tool in sysrescue-customize xorriso mksquashfs file; do
  command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 2; }
done
file "$binary" | grep -Eq 'ELF 64-bit LSB .*x86-64' || { echo "Not an x86-64 ELF" >&2; exit 3; }
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
recipe="$scratch/recipe"
mkdir -p "$recipe/iso_add/sysrescue.d" "$recipe/build_into_srm/opt/redeti-appliance/bin"
cp "$root/appliance/boot/900-redeti-appliance.yaml" "$recipe/iso_add/sysrescue.d/"
cp "$root/appliance/probe.py" "$recipe/build_into_srm/opt/redeti-appliance/probe.py"
cp "$root/appliance/boot/launch.sh" "$recipe/build_into_srm/opt/redeti-appliance/launch.sh"
install -m 0755 "$binary" "$recipe/build_into_srm/opt/redeti-appliance/bin/redeti-ui"
# Ship static Tailscale binaries and remote scripts; NEVER bundle auth keys.
tsout="${REDETI_APPLIANCE_WORK:-$HOME/RecoveryOS/native-build}/out"
for name in tailscale tailscaled; do
  [ -s "$tsout/$name" ] && [ -f "$tsout/$name.sha256" ] || { echo "Missing Tailscale binary: $name" >&2; exit 4; }
  (cd "$tsout" && sha256sum -c "$name.sha256" >/dev/null)
  install -m 0755 "$tsout/$name" "$recipe/build_into_srm/opt/redeti-appliance/bin/$name"
done
mkdir -p "$recipe/build_into_srm/opt/redeti-appliance/remote"
cp "$root/appliance/remote/provision.py" "$recipe/build_into_srm/opt/redeti-appliance/remote/provision.py"
install -m 0755 "$root/appliance/remote/start.sh" "$recipe/build_into_srm/opt/redeti-appliance/remote/start.sh"
# Prevent stock OpenSSH from listening on LAN even if enabled in a base ISO.
mkdir -p "$recipe/build_into_srm/etc/systemd/system"
ln -s /dev/null "$recipe/build_into_srm/etc/systemd/system/sshd.service"
ln -s /dev/null "$recipe/build_into_srm/etc/systemd/system/sshd.socket"
sysrescue-customize --auto --source="$source_iso" --dest="$output" --recipe-dir="$recipe"
