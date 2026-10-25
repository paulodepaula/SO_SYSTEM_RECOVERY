#!/usr/bin/env bash
# RedeTI Recovery OS: temporary private VPN over Tailscale.
# No public listener, no embedded credential; same hardened OpenSSH on LAN/VPN.
set -euo pipefail
umask 077

base=/run/redeti
socket="$base/tailscaled.sock"
ts=/opt/redeti-appliance/bin/tailscale
daemon=/opt/redeti-appliance/bin/tailscaled
provision_script=/opt/redeti-appliance/remote/provision.py
mkdir -p "$base"
chmod 0700 "$base"

status() {
  # Fixed, non-secret state codes and a validated tailnet IPv4 address only.
  printf '{"state":"%s","ssh_user":"paulo","vpn_ip":"%s"}\n' "$1" "${2:-}" > "$base/remote-status.json.tmp"
  chmod 0644 "$base/remote-status.json.tmp"
  mv -f "$base/remote-status.json.tmp" "$base/remote-status.json"
}
status "starting"
trap 'status "bootstrap_failed"' ERR

# Live SystemRescue: transient host, no passwords and no storage on client disks.
if ! id paulo >/dev/null 2>&1; then
  useradd --create-home --user-group --shell /usr/bin/bash --password '*' paulo
fi
usermod --password '*' paulo
if [ ! -x "$ts" ] || [ ! -x "$daemon" ]; then
  status "vpn_binary_missing"
  exit 1
fi
if ! command -v iptables >/dev/null 2>&1; then
  status "firewall_unverified"
  exit 1
fi

# Provision a short-lived, tagged Tailscale auth key from the physical USB.
# The ISO contains this code but NEVER contains the key itself. A key is
# copied only to tmpfs, then removed before returning.
auth_file="$base/ts-authkey"
provision="$base/vpn-provision"
install -d -m 0700 "$provision"
cleanup() {
  rm -f -- "$auth_file"
  # Unmount only a mount that this script owns; never remove Ventoy's mount.
  if [ "${mounted_here:-false}" = true ]; then
    umount -- "$provision" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

found=false
for attempt in $(seq 1 15); do
  # source candidates are restricted to USB Ventoy/REDETI_CFG FAT/exFAT and
  # validated device-mapper aliases, not customer SATA/NVMe partitions.
  mapfile -t sources < <(python3 "$provision_script" sources 2>/dev/null || true)
  for source in "${sources[@]}"; do
    keyroot=""
    mounted_here=false
    existing="$(findmnt -r -n -S "$source" -o TARGET 2>/dev/null | sed -n '1p' || true)"
    if [[ "$existing" = /* && "$existing" != "/" && -d "$existing" && ! -L "$existing" ]]; then
      keyroot="$existing"
    elif mount -o ro,nosuid,nodev,noexec -- "$source" "$provision" 2>/dev/null; then
      keyroot="$provision"
      mounted_here=true
    else
      continue
    fi
    file="$keyroot/REDETI/ts-authkey"
    if [ -d "$keyroot/REDETI" ] && [ ! -L "$keyroot/REDETI" ] &&
       [ -f "$file" ] && [ ! -L "$file" ]; then
      # Never echo/trace auth key. Strict format/length; no other USB files.
      if python3 - "$file" "$auth_file" <<'PY'
import os, pathlib, re, sys
src, dst = map(pathlib.Path, sys.argv[1:])
try:
    value = src.read_bytes()
    key = value.decode("ascii").strip()
except (OSError, UnicodeDecodeError):
    raise SystemExit(2)
if len(value) > 300 or not re.fullmatch(r"tskey-auth-[A-Za-z0-9_-]{10,240}", key):
    raise SystemExit(2)
fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "w", encoding="ascii") as stream:
    stream.write(key + "\n")
PY
      then
        found=true
      else
        status "invalid_auth_key"
      fi
    fi
    if [ "$mounted_here" = true ]; then
      umount -- "$provision" >/dev/null 2>&1 || true
      mounted_here=false
    fi
    # The first readable validated partition is authoritative.
    break
  done
  if [ "$found" = true ]; then break; fi
  if [ -f "$auth_file" ]; then rm -f -- "$auth_file"; fi
  sleep 2
done
if [ "$found" != true ]; then
  status "awaiting_provision"
  exit 0
fi
status "connecting"

# Tailscale sessions are ephemeral: state lives in RAM, never in client disks.
systemd-run --quiet --collect --unit=redeti-tailscaled \
  --property=Restart=on-failure --property=RestartSec=2 \
  "$daemon" --state=mem: --socket="$socket" >/dev/null
for attempt in $(seq 1 40); do
  [ -S "$socket" ] && break
  sleep 0.5
done
if [ ! -S "$socket" ]; then
  status "vpn_daemon_failed"
  exit 1
fi

# Don't activate Tailscale SSH. The LAN's hardened sshd + USB Ed25519 key is
# reused over the private WireGuard network, without an alternate auth path.
suffix="$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
hostname="redeti-recovery-$suffix"
if ! timeout 150 "$ts" --socket="$socket" up \
  --auth-key="file:$auth_file" \
  --ssh=false --hostname="$hostname" --advertise-tags=tag:redeti-recovery \
  --accept-routes=false --accept-dns=false \
  >> "$base/remote.log" 2>&1; then
  status "vpn_auth_failed"
  exit 1
fi
rm -f -- "$auth_file"

# Tailnet policy must allow only authorized technicians to reach this tag
# on port 22. Host firewall additionally denies ALL other tailnet ingress,
# and denies new outbound tailnet connections from the client machine.
ip="$("$ts" --socket="$socket" ip -4 2>/dev/null | sed -n '1p')"
if [[ ! "$ip" =~ ^100\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
  "$ts" --socket="$socket" down >/dev/null 2>&1 || true
  status "vpn_no_ip"
  exit 1
fi
if ! {
  iptables -N REDETI_VPN_INPUT 2>/dev/null || iptables -F REDETI_VPN_INPUT
  iptables -A REDETI_VPN_INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A REDETI_VPN_INPUT -d "$ip/32" -p tcp --dport 22 -j ACCEPT
  iptables -A REDETI_VPN_INPUT -j DROP
  iptables -I INPUT 1 -i tailscale0 -j REDETI_VPN_INPUT
  iptables -I OUTPUT 1 -o tailscale0 -m conntrack --ctstate NEW -j DROP
}; then
  "$ts" --socket="$socket" down >/dev/null 2>&1 || true
  status "firewall_blocked"
  exit 1
fi

# The network connection is ready; SSH additionally requires the USB public
# key state ready in lan-ssh-status.json (shown separately on the dashboard).
status "connected" "$ip"
