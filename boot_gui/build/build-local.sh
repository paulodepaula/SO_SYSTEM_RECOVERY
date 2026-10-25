#!/usr/bin/env bash
# RedeTI Recovery OS - build local sem comandos sobre dispositivos de clientes.
# Uso: bash boot_gui/build/build-local.sh /caminho/systemrescue-13.02-amd64.iso [pasta-saida]
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Uso: bash boot_gui/build/build-local.sh /caminho/systemrescue-13.02-amd64.iso [pasta-saida]" >&2
  exit 2
fi
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
base="$(realpath -e -- "$1")"
outdir="${2:-$HOME/RecoveryOS/out}"
mkdir -p -- "$outdir"
outdir="$(realpath -e -- "$outdir")"

if [ ! -f "$base" ] || [ ! -r "$base" ] || [ "$(basename -- "$base")" != "systemrescue-13.02-amd64.iso" ]; then
  echo "ERRO: ISO-base deve ser arquivo legivel systemrescue-13.02-amd64.iso." >&2
  exit 2
fi

expected="ad4d670b72859d887c7960142a9a9d36a3e50446694a035e254442f65d6e7572"
actual="$(sha256sum -- "$base" | cut -d ' ' -f 1)"
if [ "$actual" != "$expected" ]; then
  echo "ERRO: checksum da ISO-base difere do SystemRescue 13.02 oficial." >&2
  echo "SHA-256 calculado: $actual" >&2
  exit 3
fi

for tool in sysrescue-customize xorriso mksquashfs sha256sum; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "ERRO: dependencia ausente: $tool. Consulte boot_gui/README.md." >&2
    exit 4
  fi
done

free_kb="$(df -Pk -- "$outdir" | awk 'NR==2 {print $4}')"
if [ -z "$free_kb" ] || [ "$free_kb" -lt 8388608 ]; then
  echo "ERRO: reserve 8 GiB livres no volume de saida." >&2
  exit 5
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
image="$outdir/RedeTI-Recovery-OS-alpha-$stamp.iso"
if [ -e "$image" ]; then
  echo "ERRO: nao vou sobrescrever uma ISO existente." >&2
  exit 6
fi

echo "Base validada. Construindo $image"
bash "$root/boot_gui/build/compose_iso.sh" "$base" "$image"
if [ ! -s "$image" ]; then
  echo "ERRO: ISO nao produzida." >&2
  exit 7
fi

xorriso -indev "$image" -ls /sysresccd >/dev/null 2>&1
xorriso -indev "$image" -ls /sysrescue.d >/dev/null 2>&1
(
  cd -- "$outdir"
  sha256sum -- "$(basename -- "$image")" > "$(basename -- "$image").sha256"
)
# Retention: only after both ISO structure checks and SHA256 generation pass.
# Never touch the cached SystemRescue base or unrelated files.
bash "$root/scripts/prune-recovery-isos.sh" --apply "$outdir" "$image"
printf '\nISO: %s\nSHA256: %s.sha256\n' "$image" "$image"
echo "Build concluido. ISOs antigas deste projeto removidas apos validacao (exceto as em uso)."
echo "Ainda e necessario homologar o boot no QEMU."
