#!/usr/bin/env bash
# Build for Arch Linux userland in an isolated Docker container on Hermes.
# No host disk devices exposed; only project read-only and dedicated build cache.
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
[ -f "$repo/appliance/native/CMakeLists.txt" ] || { echo "Project not found" >&2; exit 2; }
command -v docker >/dev/null || { echo "Docker is required on Hermes" >&2; exit 2; }
command -v git >/dev/null || { echo "Git is required for build provenance" >&2; exit 2; }
# Never certify an ELF against a commit when tracked source changes are pending.
git -C "$repo" diff --quiet && git -C "$repo" diff --cached --quiet || {
  echo "Tracked changes present; commit or revert before compiling the appliance" >&2
  exit 3
}
source_head="$(git -C "$repo" rev-parse --verify HEAD)"
work="${REDETI_APPLIANCE_WORK:-$HOME/RecoveryOS/native-build}"
mkdir -p "$work/cache" "$work/out"
work="$(realpath -e -- "$work")"
rm -f -- "$work/out/redeti-ui.commit"
echo "Compiling LVGL v9.6 direct DRM/KMS (Arch container; no ISO)."
docker run --rm --pull=missing \
  --cpus 2 --memory 4g --pids-limit 256 \
  --network bridge \
  -e REDETI_SOURCE_COMMIT="$source_head" \
  -v "$repo:/project:ro" \
  -v "$work/cache:/cache" \
  -v "$work/out:/out" \
  -w /project \
  archlinux:base-devel \
  bash -euc '
    pacman -Sy --noconfirm --needed cmake ninja pkgconf libdrm libevdev json-c git python python-pillow nodejs npm ttf-dejavu
    /usr/bin/python3 -c "from PIL import Image"
    cmake -S /project/appliance/native -B /cache/lvgl -G Ninja -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE=/usr/bin/python3 -DREDETI_SOURCE_COMMIT="$REDETI_SOURCE_COMMIT"
    cmake --build /cache/lvgl --parallel 2
    ctest --test-dir /cache/lvgl --output-on-failure
    install -m 0755 /cache/lvgl/redeti-ui /out/redeti-ui
    file /out/redeti-ui
    install -m 0644 /cache/lvgl/redeti-build-id.txt /out/redeti-ui.buildinfo
    grep -Fx "source_commit=$REDETI_SOURCE_COMMIT" /out/redeti-ui.buildinfo >/dev/null
    build_tag="$(sed -n "s/^build_tag=//p" /out/redeti-ui.buildinfo)"
    [[ "$build_tag" =~ ^b[0-9]{6}-[0-9]{6}$ ]] || {
      echo "Invalid native build tag" >&2
      exit 4
    }
    strings /out/redeti-ui | grep -Fx "$build_tag" >/dev/null || {
      echo "Compiled UI does not contain current build tag" >&2
      exit 4
    }
    # Verify the revision is actually embedded in the displayed UI.
    source_rev_short="${REDETI_SOURCE_COMMIT:0:8}"
    strings /out/redeti-ui | grep -Fx "$source_rev_short" >/dev/null || {
      echo "Compiled UI is missing its source revision" >&2
      exit 4
    }
    ldd /out/redeti-ui
    (cd /out && sha256sum redeti-ui > redeti-ui.sha256)
  '
# Bind the tested executable to the exact Git commit that produced it.
# The ISO builder refuses a stale ELF even when its SHA256 sidecar is valid.
if [ "$(git -C "$repo" rev-parse --verify HEAD)" != "$source_head" ] ||
   ! git -C "$repo" diff --quiet ||
   ! git -C "$repo" diff --cached --quiet; then
  rm -f -- "$work/out/redeti-ui.commit"
  echo "Source changed during compilation; refusing to attest the ELF" >&2
  exit 3
fi
printf '%s\n' "$source_head" > "$work/out/redeti-ui.commit"
echo "Compiled source commit: $source_head"
echo "Executable: $work/out/redeti-ui"
echo "WARNING: ABI compatibility must still be verified in SystemRescue/QEMU."
