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
# Customize BIOS Syslinux and UEFI GRUB in the unpacked ISO.
mkdir -p "$recipe/iso_patch_and_script"
install -m 0755 "$root/appliance/boot/customize-boot.sh" "$recipe/iso_patch_and_script/10-redeti-boot"
install -m 0755 "$root/appliance/boot/splash.py" "$recipe/build_into_srm/opt/redeti-appliance/splash.py"
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
install -m 0755 "$root/appliance/remote/enrollment-agent.py" "$recipe/build_into_srm/opt/redeti-appliance/remote/enrollment-agent.py"
install -m 0644 "$root/appliance/remote/enrollment_client.py" "$recipe/build_into_srm/opt/redeti-appliance/remote/enrollment_client.py"
install -m 0755 "$root/appliance/remote/lan-start.sh" "$recipe/build_into_srm/opt/redeti-appliance/remote/lan-start.sh"
cp "$root/appliance/remote/lan.py" "$recipe/build_into_srm/opt/redeti-appliance/remote/lan.py"
install -m 0644 "$root/appliance/remote/sshd_config" "$recipe/build_into_srm/opt/redeti-appliance/remote/sshd_config"
install -m 0644 "$root/appliance/remote/ssh-banner.txt" "$recipe/build_into_srm/opt/redeti-appliance/remote/ssh-banner.txt"
# Read-only diagnostic for the next physical boot; never changes firewall.
install -m 0755 "$root/appliance/remote/ssh-diagnose.py" "$recipe/build_into_srm/opt/redeti-appliance/remote/ssh-diagnose.py"
# Mask the stock SSH daemon: LAN SSH uses the explicitly hardened daemon above.
mkdir -p "$recipe/build_into_srm/etc/systemd/system/sysinit.target.wants"
ln -s /dev/null "$recipe/build_into_srm/etc/systemd/system/sshd.service"
ln -s /dev/null "$recipe/build_into_srm/etc/systemd/system/sshd.socket"
# Start the lightweight framebuffer splash in the first real userspace target.
# The initramfs has no Python/renderer and is intentionally left unchanged.
install -m 0644 "$root/appliance/boot/redeti-early-splash.service" \
  "$recipe/build_into_srm/etc/systemd/system/redeti-early-splash.service"
ln -s ../redeti-early-splash.service \
  "$recipe/build_into_srm/etc/systemd/system/sysinit.target.wants/redeti-early-splash.service"
sysrescue-customize --auto --source="$source_iso" --dest="$output" --recipe-dir="$recipe"
