#!/usr/bin/env bash
# Testa a ISO somente em VM 64-bit, sem discos virtuais ou fisicos.
# Uso: bash boot_gui/build/test-qemu-x64.sh /caminho/RedeTI-Recovery-OS-alpha.iso
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Uso: bash boot_gui/build/test-qemu-x64.sh /caminho/arquivo.iso" >&2
  exit 2
fi
iso="$(realpath -e -- "$1")"
if [ ! -f "$iso" ] || [ ! -r "$iso" ]; then
  echo "ISO inexistente ou sem permissao de leitura" >&2
  exit 2
fi
if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
  echo "Instale qemu-system-x86 (Ubuntu/Debian)" >&2
  exit 3
fi

# KVM: expor CPU real de 64 bits; sem KVM: emular CPU 64 bits.
if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
  cpu_args=(-accel kvm -cpu host)
  echo "QEMU: CPU x86_64 acelerada com KVM"
else
  cpu_args=(-accel tcg -cpu max)
  echo "QEMU: CPU x86_64 emulada (TCG, mais lenta)"
fi

# Para servidor headless: VNC so em loopback, nao expor porta na rede.
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
  video_args=(-display gtk)
  echo "Video: janela grafica local"
else
  video_args=(-display none -vnc 127.0.0.1:0)
  echo "Video: VNC local em 127.0.0.1:5900; use tunel SSH para acesso remoto"
fi

echo "ISO: $iso"
echo "Sem HDD/SSD conectado e sem rede na maquina virtual."
exec qemu-system-x86_64 \
  -machine q35 \
  "${cpu_args[@]}" \
  -m 3072 -smp 2 \
  -boot order=d \
  -drive "file=$iso,media=cdrom,readonly=on" \
  -nic none \
  -vga std \
  "${video_args[@]}"
