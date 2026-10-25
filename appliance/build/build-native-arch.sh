#!/usr/bin/env bash
# Build for Arch Linux userland in an isolated Docker container on Hermes.
# No host disk devices exposed; only project read-only and dedicated build cache.
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
[ -f "$repo/appliance/native/CMakeLists.txt" ] || { echo "Project not found" >&2; exit 2; }
command -v docker >/dev/null || { echo "Docker is required on Hermes" >&2; exit 2; }
work="${REDETI_APPLIANCE_WORK:-$HOME/RecoveryOS/native-build}"
mkdir -p "$work/cache" "$work/out"
work="$(realpath -e -- "$work")"
echo "Compiling LVGL v9.6 direct DRM/KMS (Arch container; no ISO)."
docker run --rm --pull=missing \
  --cpus 2 --memory 4g --pids-limit 256 \
  --network bridge \
  -v "$repo:/project:ro" \
  -v "$work/cache:/cache" \
  -v "$work/out:/out" \
  -w /project \
  archlinux:base-devel \
  bash -euc '
    pacman -Sy --noconfirm --needed cmake ninja pkgconf libdrm json-c git python python-pillow
    /usr/bin/python3 -c "from PIL import Image"
    cmake -S /project/appliance/native -B /cache/lvgl -G Ninja -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE=/usr/bin/python3
    cmake --build /cache/lvgl --parallel 2
    install -m 0755 /cache/lvgl/redeti-ui /out/redeti-ui
    file /out/redeti-ui
    ldd /out/redeti-ui
    sha256sum /out/redeti-ui > /out/redeti-ui.sha256
  '
echo "Executable: $work/out/redeti-ui"
echo "WARNING: ABI compatibility must still be verified in SystemRescue/QEMU."
