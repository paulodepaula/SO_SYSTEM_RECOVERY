#!/usr/bin/env bash
# Compose ISO on a separate trusted Linux builder, NOT client media.
# Usage: bash boot_gui/build/compose_iso.sh source.iso output.iso
set -euo pipefail
[ "$#" -eq 2 ] || { echo "Expected source and output ISO paths" >&2; exit 2; }
source_iso=$(realpath -e -- "$1")
output_iso=$(realpath -m -- "$2")
root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
[ "$source_iso" != "$output_iso" ] || { echo "Source and output cannot match" >&2; exit 2; }
[ ! -e "$output_iso" ] || { echo "Output exists; refusing overwrite" >&2; exit 2; }
for name in sysrescue-customize xorriso mksquashfs; do
  command -v "$name" >/dev/null || { echo "Missing program: $name" >&2; exit 2; }
done
temp=$(mktemp -d)
trap 'rm -rf -- "$temp"' EXIT
recipe="$temp/recipe"
mkdir -p "$recipe/iso_add/sysrescue.d" "$recipe/build_into_srm/opt/redeti-recovery"
cp "$root/boot_gui/recipe/iso_add/sysrescue.d/700-redeti.yaml" "$recipe/iso_add/sysrescue.d/"
cp -R "$root/boot_gui/app" "$root/boot_gui/ui" "$root/boot_gui/build" "$recipe/build_into_srm/opt/redeti-recovery/"
if [ -f "$root/assets/logo-paulo.svg" ]; then
  mkdir -p "$recipe/build_into_srm/opt/redeti-recovery/ui/assets"
  cp "$root/assets/logo-paulo.svg" "$recipe/build_into_srm/opt/redeti-recovery/ui/assets/"
fi
sysrescue-customize --auto --source="$source_iso" --dest="$output_iso" --recipe-dir="$recipe"
echo "ISO created: $output_iso"
