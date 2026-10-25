#!/usr/bin/env bash
# RedeTI Recovery OS: remove old project ISOs only after a verified build.
# Usage: bash scripts/prune-recovery-isos.sh --dry-run|--apply OUTPUT_DIR KEEP_ISO
set -euo pipefail
if [ "$#" -ne 3 ] || { [ "$1" != "--dry-run" ] && [ "$1" != "--apply" ]; }; then
  echo "Uso: bash scripts/prune-recovery-isos.sh --dry-run|--apply PASTA_SAIDA ISO_VALIDADA" >&2
  exit 2
fi
mode="$1"
outdir="$(realpath -e -- "$2")"
keep="$(realpath -e -- "$3")"
keepname="$(basename -- "$keep")"
if [ ! -d "$outdir" ] || [ "$outdir" = "/" ] || [ "$outdir" = "$HOME" ]; then
  echo "ERRO: pasta de saida perigosa." >&2
  exit 2
fi
case "$outdir" in
  */base|*/base/*) echo "ERRO: pasta da ISO-base protegida." >&2; exit 2 ;;
esac
if [ "$(dirname -- "$keep")" != "$outdir" ] || [ ! -f "$keep" ] || [ -L "$keep" ]; then
  echo "ERRO: a ISO a preservar deve ser arquivo regular nesta pasta." >&2
  exit 3
fi
if [[ ! "$keepname" =~ ^RedeTI-Recovery-OS-(alpha|appliance)(-[0-9]{8}T[0-9]{6}Z)?\.iso$ ]]; then
  echo "ERRO: nome da ISO fora do padrao gerenciado." >&2
  exit 3
fi
if [ ! -f "$keep.sha256" ] || [ -L "$keep.sha256" ]; then
  echo "ERRO: checksum da nova ISO ausente. Nao limpar ISOs." >&2
  exit 4
fi
expected="$(awk 'NR==1 {print $1}' "$keep.sha256")"
if [[ ! "$expected" =~ ^[[:xdigit:]]{64}$ ]]; then
  echo "ERRO: checksum da nova ISO invalido. Nao limpar ISOs." >&2
  exit 4
fi
actual="$(sha256sum -- "$keep" | cut -d ' ' -f 1)"
if [ "$expected" != "$actual" ]; then
  echo "ERRO: nova ISO nao corresponde ao checksum. Nao limpar ISOs." >&2
  exit 4
fi
shopt -s nullglob
removed=0
skipped=0
for file in "$outdir"/RedeTI-Recovery-OS-*.iso; do
  [ "$file" = "$keep" ] && continue
  [ -f "$file" ] && [ ! -L "$file" ] || continue
  filename="$(basename -- "$file")"
  if [[ ! "$filename" =~ ^RedeTI-Recovery-OS-(alpha|appliance)(-[0-9]{8}T[0-9]{6}Z)?\.iso$ ]]; then
    continue
  fi
  if command -v fuser >/dev/null 2>&1 && fuser -s -- "$file" 2>/dev/null; then
    echo "PRESERVADA (em uso): $filename"
    skipped=$((skipped + 1))
    continue
  fi
  if [ "$mode" = "--dry-run" ]; then
    echo "SERIA REMOVIDA: $filename"
  else
    rm -- "$file"
    if [ -f "$file.sha256" ] && [ ! -L "$file.sha256" ]; then
      rm -- "$file.sha256"
    fi
    echo "REMOVIDA: $filename"
  fi
  removed=$((removed + 1))
done
echo "ISO preservada: $keepname"
echo "Candidatas processadas: $removed | Em uso: $skipped | Modo: $mode"
