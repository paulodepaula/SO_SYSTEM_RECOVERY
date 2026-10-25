#!/usr/bin/env bash
# Remote administration for temporary RecoveryOS sessions.
# Tailscale SSH only: no OpenSSH listener, static password, or keys in ISO.
set -euo pipefail
umask 077

base=/run/redeti
socket="$base/tailscaled.sock"
ts=/opt/redeti-appliance/bin/tailscale
daemon=/opt/redeti-appliance/bin/tailscaled
mkdir -p "$base"
chmod 0700 "$base"

status() {
  # Only fixed strings and validated IPv4 addresses are accepted below.
  printf '{"state":"%s","ssh_user":"redeti","vpn_ip":"%s"}\n' "$1" "${2:-}" > "$base/remote-status.json.tmp"
  chmod 0644 "$base/remote-status.json.tmp"
  mv -f "$base/remote-status.json.tmp" "$base/remote-status.json"
}

status "starting"
# Do not expose the preinstalled SystemRescue OpenSSH daemon on LAN.
systemctl mask --runtime --now sshd.service >/dev/null 2>&1 || true
if ! id redeti >/dev/null 2>&1; then
  useradd --create-home --user-group --shell /usr/bin/bash redeti
fi
# The Tailscale SSH policy authenticates users. No password-based fallback.
passwd -l redeti >/dev/null 2>&1 || true

if [ ! -x "$ts" ] || [ ! -x "$daemon" ]; then
  status "vpn_binary_missing"
  exit 1
fi

# Only a labelled USB Ventoy/REDETI_CFG exFAT/FAT volume is considered.
# Internal NTFS disks are never searched or mounted.
device="$(python3 /opt/redeti-appliance/remote/provision.py)" || {
  status "awaiting_provision"
  exit 0
}
provision="$base/provision"
mkdir -p "$provision"
if ! mount -o ro,nosuid,nodev,noexec -- "$device" "$provision"; then
  status "provision_mount_failed"
  exit 1
fi
cleanup_mount() {
  mountpoint -q "$provision" && umount -- "$provision" || true
}
trap cleanup_mount EXIT
input="$provision/REDETI/ts-authkey"
if [ ! -f "$input" ] || [ -L "$input" ]; then
  status "awaiting_provision"
  exit 0
fi
# Validate the credential without printing or interpolating it into argv.
python3 - "$input" "$base/ts-authkey" <<'PY'
import pathlib, re, sys, os
src, dst = map(pathlib.Path, sys.argv[1:])
key = src.read_text(encoding="ascii").strip()
if not re.fullmatch(r"tskey-auth-[A-Za-z0-9_-]{10,240}", key):
    raise SystemExit("Invalid Tailscale auth key format")
fd = os.open(dst, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
with os.fdopen(fd, "w") as stream:
    stream.write(key + "\n")
PY
cleanup_mount
trap - EXIT
status "connecting"
# Keep everything in RAM. Each boot becomes an ephemeral tailnet node.
systemd-run --quiet --collect --unit=redeti-tailscaled \
  --property=Restart=on-failure --property=RestartSec=2 \
  "$daemon" --state=mem: --socket="$socket" >/dev/null
for _ in $(seq 1 40); do
  [ -S "$socket" ] && break
  sleep 0.5
done
if [ ! -S "$socket" ]; then
  rm -f "$base/ts-authkey"
  status "vpn_daemon_failed"
  exit 1
fi

# Random session name prevents conflicts when multiple computers boot the ISO.
suffix="$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
hostname="redeti-recovery-$suffix"
# --auth-key=file: avoids passing the secret in process argv or shell history.
# --ssh enables Tailscale SSH only on this device's tailnet address.
if ! timeout 150 "$ts" --socket="$socket" up \
  --auth-key="file:$base/ts-authkey" \
  --ssh --hostname="$hostname" \
  --accept-routes=false --accept-dns=false \
  >> "$base/remote.log" 2>&1; then
  rm -f "$base/ts-authkey"
  status "vpn_auth_failed"
  exit 1
fi
rm -f "$base/ts-authkey"
ip="$("$ts" --socket="$socket" ip -4 2>/dev/null | head -n1)"
if [[ "$ip" =~ ^100\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
  status "connected" "$ip"
else
  status "vpn_no_ip"
fi
