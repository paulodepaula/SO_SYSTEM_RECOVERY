#!/usr/bin/env bash
# Download official version-pinned static Tailscale for embedding in the ISO.
# No credentials are downloaded or embedded.
set -euo pipefail
version=1.104.2
work="${REDETI_APPLIANCE_WORK:-$HOME/RecoveryOS/native-build}"
out="$work/out"
mkdir -p "$out"
for name in tailscale tailscaled; do
  if [ -s "$out/$name" ] && [ -f "$out/$name.sha256" ]; then
    (cd "$out" && sha256sum -c "$name.sha256" >/dev/null) || exit 2
  fi
done
if [ -s "$out/tailscale" ] && [ -s "$out/tailscaled" ]; then
  "$out/tailscale" version | grep -F "$version" >/dev/null || { echo "Wrong Tailscale version" >&2; exit 2; }
  echo "Tailscale binaries already available: $version"
  exit 0
fi
command -v curl >/dev/null || { echo "curl is required" >&2; exit 2; }
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
archive="tailscale_${version}_amd64.tgz"
url="https://pkgs.tailscale.com/stable/$archive"
curl --fail --location --show-error --silent --retry 3 --proto '=https' --tlsv1.2 "$url" --output "$tmp/$archive"
# The entire archive comes from the official HTTPS distributor; verify the
# extracted filenames and version before placing them into the build cache.
tar -tzf "$tmp/$archive" | grep -Fx "tailscale_${version}_amd64/tailscale" >/dev/null
tar -tzf "$tmp/$archive" | grep -Fx "tailscale_${version}_amd64/tailscaled" >/dev/null
tar --no-same-owner -xf "$tmp/$archive" -C "$tmp" \
  "tailscale_${version}_amd64/tailscale" "tailscale_${version}_amd64/tailscaled"
for name in tailscale tailscaled; do
  install -m 0755 "$tmp/tailscale_${version}_amd64/$name" "$out/$name"
  (cd "$out" && sha256sum "$name" > "$name.sha256")
done
"$out/tailscale" version | grep -F "$version" >/dev/null
echo "Tailscale $version binaries cached under $out; no auth key in ISO."
